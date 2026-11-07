"""Regression test: ``POST /runs/{id}/cancel`` must stop a run that is already running.

The worker keeps one long-lived session per run (``expire_on_commit=False``). Before the
fix, its cancellation check read the run from the session identity map, so a cancel
committed by the API in another session was never observed: the run kept ingesting
jobs, processed every remaining source and finished as ``completed``.
"""

from __future__ import annotations

import asyncio
import threading
import time
from typing import TYPE_CHECKING, Any

from fastapi.testclient import TestClient

from autoapply_agent.adapters.base import JobCandidate
from autoapply_agent.adapters.greenhouse import GreenhouseAdapter
from autoapply_agent.core.config import Settings
from autoapply_agent.main import create_app

if TYPE_CHECKING:
    from _pytest.monkeypatch import MonkeyPatch

_FETCH_STARTED = threading.Event()
_CANCEL_SENT = threading.Event()


async def _fetch_blocking_until_cancel_sent(
    self: GreenhouseAdapter,
    base_url: str,
    timeout_seconds: float,
    max_jobs: int,
) -> list[JobCandidate]:
    """Pause the first fetch until the test has cancelled the run through the API."""
    del self, timeout_seconds, max_jobs
    if not _FETCH_STARTED.is_set():
        _FETCH_STARTED.set()
        for _ in range(500):
            if _CANCEL_SENT.is_set():
                break
            await asyncio.sleep(0.01)
    return [
        JobCandidate(
            external_id=f"running-cancel-{index}",
            title=f"Python Backend Engineer {index}",
            location="Remote",
            company="example.com",
            url=f"{base_url.rstrip('/')}/jobs/running-cancel-{index}",
            raw={"fixture": "cancel-while-running"},
        )
        for index in range(3)
    ]


def test_cancel_while_running_stops_run_before_more_jobs_are_ingested(
    sqlite_database_url: str,
    monkeypatch: MonkeyPatch,
) -> None:
    """A cancel issued mid-run must end as cancelled with a single cancel event."""
    _FETCH_STARTED.clear()
    _CANCEL_SENT.clear()
    monkeypatch.setattr(GreenhouseAdapter, "fetch_jobs", _fetch_blocking_until_cancel_sent)

    settings = Settings(
        APP_NAME="autoapply-cancel-running-test",
        DATABASE_URL=sqlite_database_url,
        WORKER_POLL_INTERVAL_SECONDS=0.05,
        HTTP_TIMEOUT_SECONDS=0.5,
        MAX_JOBS_PER_SOURCE=5,
        HTTP_USER_AGENT="integration-test-agent",
        ENABLE_WORKER=True,
        ENVIRONMENT="test",
    )
    app = create_app(settings)
    with TestClient(app) as client:
        for name, board in (("cancel-first", "first"), ("cancel-second", "second")):
            source_response = client.post(
                "/source-configs",
                json={
                    "name": name,
                    "source_type": "greenhouse",
                    "base_url": f"https://boards.greenhouse.io/embed/job_board?for={board}",
                },
            )
            assert source_response.status_code == 201

        run_response = client.post("/runs", json={"query": "python backend"})
        assert run_response.status_code == 201
        run_id = run_response.json()["id"]

        assert _FETCH_STARTED.wait(timeout=5), "worker never started fetching the first source"
        cancel_response = client.post(f"/runs/{run_id}/cancel")
        assert cancel_response.status_code == 200
        assert cancel_response.json()["status"] == "cancel_requested"
        _CANCEL_SENT.set()

        status_payload: dict[str, Any] = {}
        for _ in range(100):
            status_payload = client.get(f"/runs/{run_id}").json()
            if status_payload["status"] in {"completed", "failed", "cancelled"}:
                break
            time.sleep(0.05)

        events = client.get(f"/runs/{run_id}/events").json()
        event_types = [entry["event_type"] for entry in events]
        jobs = client.get("/jobs", params={"run_id": run_id}).json()

    assert status_payload["status"] == "cancelled", event_types
    assert status_payload["cancel_requested"] is True
    assert status_payload["finished_at"] is not None
    assert event_types.count("run.cancelled") == 1, event_types
    assert "run.completed" not in event_types
    assert event_types.count("source.started") == 1, "second source must not be processed"
    assert "agent.decision" not in event_types
    assert jobs == []
    assert [entry["sequence"] for entry in events] == list(range(1, len(events) + 1))

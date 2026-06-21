"""Regression test: cancellation during active job ingestion must persist as cancelled."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from fastapi.testclient import TestClient

from autoapply_agent.adapters.base import JobCandidate
from autoapply_agent.adapters.greenhouse import GreenhouseAdapter
from autoapply_agent.core.config import Settings
from autoapply_agent.main import create_app
from autoapply_agent.services.worker import InProcessWorker

if TYPE_CHECKING:
    from _pytest.capture import CaptureFixture
    from _pytest.fixtures import FixtureRequest
    from _pytest.logging import LogCaptureFixture
    from _pytest.monkeypatch import MonkeyPatch
    from pytest_mock.plugin import MockerFixture

# Shared flag flipped to True once the adapter has fetched jobs, i.e. once the
# worker is inside the per-job loop of the only source.
_FETCH_STATE: dict[str, bool] = {"fetched": False}


async def _fake_fetch_then_arm_cancel(
    self: GreenhouseAdapter,
    base_url: str,
    timeout_seconds: float,
    max_jobs: int,
) -> list[JobCandidate]:
    """Return one job and arm cancellation for the subsequent job-loop check."""
    del self, timeout_seconds, max_jobs
    _FETCH_STATE["fetched"] = True
    return [
        JobCandidate(
            external_id="int-cancel-001",
            title="Python Backend Engineer",
            location="Remote",
            company="example.com",
            url=f"{base_url.rstrip('/')}/jobs/int-cancel-001",
            raw={"fixture": "cancel"},
        )
    ]


async def _cancel_after_fetch(self: InProcessWorker, session: Any, run_id: str) -> bool:
    """Report cancellation only after the source's jobs have been fetched.

    This makes the source-loop check (before fetch) return ``False`` so the
    source is processed, then makes the per-job check (after fetch) return
    ``True`` so cancellation fires while ingesting the only source's jobs.
    """
    del self, session, run_id
    return _FETCH_STATE["fetched"]


def test_cancel_during_last_source_persists_cancelled(
    sqlite_database_url: str,
    monkeypatch: MockerFixture,
) -> None:
    """Cancelling while ingesting the only source must end as cancelled, not completed."""
    _FETCH_STATE["fetched"] = False
    monkeypatch.setattr(GreenhouseAdapter, "fetch_jobs", _fake_fetch_then_arm_cancel)
    monkeypatch.setattr(InProcessWorker, "_is_cancel_requested", _cancel_after_fetch)

    settings = Settings(
        APP_NAME="autoapply-cancel-test",
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
        source_response = client.post(
            "/source-configs",
            json={
                "name": "integration-greenhouse-cancel",
                "source_type": "greenhouse",
                "base_url": "https://boards.greenhouse.io/embed/job_board?for=example",
            },
        )
        assert source_response.status_code == 201

        run_response = client.post("/runs", json={"query": "python backend"})
        assert run_response.status_code == 201
        run_id = run_response.json()["id"]

        status_payload: dict[str, Any] = {}
        for _ in range(60):
            status_response = client.get(f"/runs/{run_id}")
            assert status_response.status_code == 200
            status_payload = status_response.json()
            if status_payload["status"] in {"completed", "failed", "cancelled"}:
                break
            time.sleep(0.05)

        assert status_payload["status"] == "cancelled"

        events_response = client.get(f"/runs/{run_id}/events")
        assert events_response.status_code == 200
        event_types = [entry["event_type"] for entry in events_response.json()]
        assert "run.cancelled" in event_types
        assert "run.completed" not in event_types

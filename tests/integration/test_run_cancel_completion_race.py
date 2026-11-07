"""Regression test: a cancel that races the run's completion must not un-finish it.

``POST /runs/{id}/cancel`` reads the run and then writes its decision. On SQLite that
write waits for the worker's open write transaction (the worker holds it while it
ingests a source), and the worker completes the run as soon as that transaction
commits. The handler used to write the status it derived from its earlier read, so a
cancel sent while the last source was being ingested turned the ``completed`` run into
``cancel_requested`` — a non-terminal status the finished worker never leaves, so
clients polling for a terminal status waited forever.

The test pins that interleaving: the worker pauses with its ``completed`` status and
``run.completed`` event flushed but not committed (so it holds the write lock) until
the cancel request has read the run and issues its ``UPDATE``.
"""

from __future__ import annotations

import asyncio
import threading
from typing import TYPE_CHECKING, Any

from fastapi.testclient import TestClient
from sqlalchemy import event

from autoapply_agent.adapters.base import JobCandidate
from autoapply_agent.adapters.greenhouse import GreenhouseAdapter
from autoapply_agent.core.config import Settings
from autoapply_agent.db.models import RunEvent
from autoapply_agent.main import create_app
from autoapply_agent.services import worker as worker_module

if TYPE_CHECKING:
    from _pytest.monkeypatch import MonkeyPatch
    from sqlalchemy.ext.asyncio import AsyncSession

_COMPLETION_FLUSHED = threading.Event()
_CANCEL_WRITE_STARTED = threading.Event()


async def _fetch_one_job(
    self: GreenhouseAdapter,
    base_url: str,
    timeout_seconds: float,
    max_jobs: int,
) -> list[JobCandidate]:
    """Serve a single posting for the run's only source."""
    del self, timeout_seconds, max_jobs
    return [
        JobCandidate(
            external_id="race-0",
            title="Python Backend Engineer",
            location="Remote",
            company="example.com",
            url=f"{base_url.rstrip('/')}/jobs/race-0",
            raw={"fixture": "cancel-completion-race"},
        )
    ]


def test_cancel_racing_run_completion_keeps_the_run_completed(
    sqlite_database_url: str,
    monkeypatch: MonkeyPatch,
) -> None:
    """A run that finishes while a cancel request is in flight stays ``completed``."""
    _COMPLETION_FLUSHED.clear()
    _CANCEL_WRITE_STARTED.clear()
    append_run_event = worker_module.append_run_event

    async def append_then_pause_on_completion(
        session: AsyncSession,
        run_id: str,
        event_type: str,
        message: str,
        payload: dict[str, object] | None = None,
    ) -> RunEvent:
        run_event = await append_run_event(session, run_id, event_type, message, payload)
        if event_type == "run.completed":
            # Flushed, not committed: the worker now holds SQLite's write lock.
            _COMPLETION_FLUSHED.set()
            for _ in range(1000):
                if _CANCEL_WRITE_STARTED.is_set():
                    break
                await asyncio.sleep(0.01)
        return run_event

    def flag_cancel_write(
        conn: Any, cursor: Any, statement: str, *args: Any, **kwargs: Any
    ) -> None:
        del conn, cursor, args, kwargs
        if statement.startswith("UPDATE runs") and "cancel_requested" in statement:
            _CANCEL_WRITE_STARTED.set()

    monkeypatch.setattr(GreenhouseAdapter, "fetch_jobs", _fetch_one_job)
    monkeypatch.setattr(worker_module, "append_run_event", append_then_pause_on_completion)

    settings = Settings(
        APP_NAME="autoapply-cancel-race-test",
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
                "name": "cancel-race",
                "source_type": "greenhouse",
                "base_url": "https://boards.greenhouse.io/embed/job_board?for=race",
            },
        )
        assert source_response.status_code == 201
        run_response = client.post("/runs", json={"query": "python backend"})
        assert run_response.status_code == 201
        run_id = run_response.json()["id"]

        assert _COMPLETION_FLUSHED.wait(timeout=5), "worker never reached run completion"
        engine = app.state.engine.sync_engine
        event.listen(engine, "before_cursor_execute", flag_cancel_write)
        try:
            cancel_response = client.post(f"/runs/{run_id}/cancel")
        finally:
            _CANCEL_WRITE_STARTED.set()
            event.remove(engine, "before_cursor_execute", flag_cancel_write)

        run_payload = client.get(f"/runs/{run_id}").json()
        event_types = [entry["event_type"] for entry in client.get(f"/runs/{run_id}/events").json()]
        jobs = client.get("/jobs", params={"run_id": run_id}).json()

    assert cancel_response.status_code == 200
    assert run_payload["status"] == "completed", f"events: {event_types}"
    assert run_payload["cancel_requested"] is False
    assert cancel_response.json()["status"] == "completed"
    assert event_types[-2:] == ["run.completed", "run.cancel_ignored"], f"events: {event_types}"
    assert "run.cancel_requested" not in event_types
    assert [job["external_id"] for job in jobs] == ["race-0"]

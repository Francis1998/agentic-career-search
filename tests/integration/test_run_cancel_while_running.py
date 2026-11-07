"""Regression tests: ``POST /runs/{id}/cancel`` must stop a run that is already running.

The worker keeps one long-lived session per run (``expire_on_commit=False``). Before the
fix, its cancellation check read the run from the session identity map, so a cancel
committed by the API in another session was never observed: the run kept ingesting
jobs, processed every remaining source and finished as ``completed``.

A cancel committed while the final source is fetching must also be honoured when that
fetch yields no jobs or fails, because neither path reaches the per-job check.
"""

from __future__ import annotations

import asyncio
import threading
import time
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

import pytest
from fastapi.testclient import TestClient

from autoapply_agent.adapters.base import JobCandidate, SourceAdapterError
from autoapply_agent.adapters.greenhouse import GreenhouseAdapter
from autoapply_agent.core.config import Settings
from autoapply_agent.main import create_app

if TYPE_CHECKING:
    from _pytest.monkeypatch import MonkeyPatch

FetchJobs = Callable[[GreenhouseAdapter, str, float, int], Awaitable[list[JobCandidate]]]

_FETCH_STARTED = threading.Event()
_CANCEL_SENT = threading.Event()


async def _pause_until_cancel_sent() -> None:
    """Signal that a fetch is in flight, then wait (max ~5 s) for the API cancel."""
    _FETCH_STARTED.set()
    for _ in range(500):
        if _CANCEL_SENT.is_set():
            return
        await asyncio.sleep(0.01)


def _jobs_for(base_url: str, count: int) -> list[JobCandidate]:
    """Build deterministic job candidates for one source."""
    return [
        JobCandidate(
            external_id=f"running-cancel-{index}",
            title=f"Python Backend Engineer {index}",
            location="Remote",
            company="example.com",
            url=f"{base_url.rstrip('/')}/jobs/running-cancel-{index}",
            raw={"fixture": "cancel-while-running"},
        )
        for index in range(count)
    ]


async def _fetch_blocking_until_cancel_sent(
    self: GreenhouseAdapter,
    base_url: str,
    timeout_seconds: float,
    max_jobs: int,
) -> list[JobCandidate]:
    """Pause the first fetch until the test has cancelled the run through the API."""
    del self, timeout_seconds, max_jobs
    if not _FETCH_STARTED.is_set():
        await _pause_until_cancel_sent()
    return _jobs_for(base_url, 3)


async def _final_fetch_returns_no_jobs(
    self: GreenhouseAdapter,
    base_url: str,
    timeout_seconds: float,
    max_jobs: int,
) -> list[JobCandidate]:
    """Serve one job from the first source; the final fetch is cancelled and empty."""
    del self, timeout_seconds, max_jobs
    if "for=final" not in base_url:
        return _jobs_for(base_url, 1)
    await _pause_until_cancel_sent()
    return []


async def _final_fetch_raises(
    self: GreenhouseAdapter,
    base_url: str,
    timeout_seconds: float,
    max_jobs: int,
) -> list[JobCandidate]:
    """Serve one job from the first source; the final fetch is cancelled and fails."""
    del self, timeout_seconds, max_jobs
    if "for=final" not in base_url:
        return _jobs_for(base_url, 1)
    await _pause_until_cancel_sent()
    raise SourceAdapterError(f"http error 503 for {base_url}")


def _cancel_mid_fetch(
    database_url: str,
    monkeypatch: MonkeyPatch,
    fetch_jobs: FetchJobs,
    boards: tuple[str, ...],
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    """Start a run, cancel it via the API while a fetch is paused, and wait for the end.

    Args:
        database_url: Isolated sqlite URL for this test.
        monkeypatch: Pytest monkeypatch fixture.
        fetch_jobs: Fake ``GreenhouseAdapter.fetch_jobs`` that calls
            ``_pause_until_cancel_sent`` for exactly one source.
        boards: Greenhouse board tokens, one source config each, in processing order.

    Returns:
        Final run payload, ordered run events, and persisted jobs for the run.
    """
    _FETCH_STARTED.clear()
    _CANCEL_SENT.clear()
    monkeypatch.setattr(GreenhouseAdapter, "fetch_jobs", fetch_jobs)

    settings = Settings(
        APP_NAME="autoapply-cancel-running-test",
        DATABASE_URL=database_url,
        WORKER_POLL_INTERVAL_SECONDS=0.05,
        HTTP_TIMEOUT_SECONDS=0.5,
        MAX_JOBS_PER_SOURCE=5,
        HTTP_USER_AGENT="integration-test-agent",
        ENABLE_WORKER=True,
        ENVIRONMENT="test",
    )
    with TestClient(create_app(settings)) as client:
        for board in boards:
            source_response = client.post(
                "/source-configs",
                json={
                    "name": f"cancel-{board}",
                    "source_type": "greenhouse",
                    "base_url": f"https://boards.greenhouse.io/embed/job_board?for={board}",
                },
            )
            assert source_response.status_code == 201

        run_response = client.post("/runs", json={"query": "python backend"})
        assert run_response.status_code == 201
        run_id = run_response.json()["id"]

        assert _FETCH_STARTED.wait(timeout=5), "worker never reached the paused fetch"
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
        jobs = client.get("/jobs", params={"run_id": run_id}).json()
    return status_payload, events, jobs


def test_cancel_while_running_stops_run_before_more_jobs_are_ingested(
    sqlite_database_url: str,
    monkeypatch: MonkeyPatch,
) -> None:
    """A cancel issued mid-run must end as cancelled with a single cancel event."""
    status_payload, events, jobs = _cancel_mid_fetch(
        sqlite_database_url,
        monkeypatch,
        _fetch_blocking_until_cancel_sent,
        ("first", "second"),
    )
    event_types = [entry["event_type"] for entry in events]

    assert status_payload["status"] == "cancelled", event_types
    assert status_payload["cancel_requested"] is True
    assert status_payload["finished_at"] is not None
    assert event_types.count("run.cancelled") == 1, event_types
    assert "run.completed" not in event_types
    assert event_types.count("source.started") == 1, "second source must not be processed"
    assert "agent.decision" not in event_types
    assert jobs == []
    assert [entry["sequence"] for entry in events] == list(range(1, len(events) + 1))


@pytest.mark.parametrize(
    ("fetch_jobs", "final_source_event"),
    [
        pytest.param(_final_fetch_returns_no_jobs, "source.completed", id="empty-final-fetch"),
        pytest.param(_final_fetch_raises, "source.failed", id="adapter-error-final-fetch"),
    ],
)
def test_cancel_during_final_fetch_without_jobs_is_honored(
    sqlite_database_url: str,
    monkeypatch: MonkeyPatch,
    fetch_jobs: FetchJobs,
    final_source_event: str,
) -> None:
    """A cancel committed while the last source fetches must win over completion.

    An empty result and a ``SourceAdapterError`` both skip the per-job cancellation
    check, so only a check after each source can observe the request.
    """
    status_payload, events, jobs = _cancel_mid_fetch(
        sqlite_database_url,
        monkeypatch,
        fetch_jobs,
        ("first", "final"),
    )
    event_types = [entry["event_type"] for entry in events]

    assert status_payload["status"] == "cancelled", event_types
    assert status_payload["cancel_requested"] is True
    assert status_payload["finished_at"] is not None
    assert event_types.count("source.started") == 2, event_types
    assert event_types[-2:] == [final_source_event, "run.cancelled"], event_types
    assert event_types.count("run.cancelled") == 1, event_types
    assert "run.completed" not in event_types
    assert [job["external_id"] for job in jobs] == ["running-cancel-0"]
    assert [entry["sequence"] for entry in events] == list(range(1, len(events) + 1))

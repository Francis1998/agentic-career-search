"""Integration tests for run lifecycle endpoints and worker processing."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from fastapi.testclient import TestClient

from autoapply_agent.adapters.base import JobCandidate
from autoapply_agent.adapters.greenhouse import GreenhouseAdapter
from autoapply_agent.core.config import Settings
from autoapply_agent.main import create_app

if TYPE_CHECKING:
    from _pytest.capture import CaptureFixture
    from _pytest.fixtures import FixtureRequest
    from _pytest.logging import LogCaptureFixture
    from _pytest.monkeypatch import MonkeyPatch
    from pytest_mock.plugin import MockerFixture


def _build_settings(database_url: str, enable_worker: bool) -> Settings:
    """Build test settings for integration tests.

    Args:
        database_url: Test sqlite URL.
        enable_worker: Worker startup toggle.

    Returns:
        Settings object.
    """

    return Settings(
        APP_NAME="autoapply-integration-test",
        DATABASE_URL=database_url,
        WORKER_POLL_INTERVAL_SECONDS=0.05,
        HTTP_TIMEOUT_SECONDS=0.5,
        MAX_JOBS_PER_SOURCE=5,
        HTTP_USER_AGENT="integration-test-agent",
        ENABLE_WORKER=enable_worker,
        ENVIRONMENT="test",
    )


async def _fake_greenhouse_fetch(
    self: GreenhouseAdapter,
    base_url: str,
    timeout_seconds: float,
    max_jobs: int,
) -> list[JobCandidate]:
    """Return deterministic fake jobs for integration testing.

    Args:
        self: Adapter instance.
        base_url: Source URL.
        timeout_seconds: Timeout provided by worker.
        max_jobs: Max jobs allowed.

    Returns:
        List with one deterministic job candidate.
    """

    del self, timeout_seconds, max_jobs
    return [
        JobCandidate(
            external_id="int-001",
            title="Python Backend Engineer",
            location="Remote",
            company="example.com",
            url=f"{base_url.rstrip('/')}/jobs/int-001",
            raw={"fixture": "integration"},
        )
    ]


def test_run_lifecycle_complete_with_worker(
    sqlite_database_url: str,
    monkeypatch: MockerFixture,
) -> None:
    """Create run and verify worker-driven completion and event persistence."""

    monkeypatch.setattr(GreenhouseAdapter, "fetch_jobs", _fake_greenhouse_fetch)

    app = create_app(_build_settings(sqlite_database_url, enable_worker=True))
    with TestClient(app) as client:
        source_response = client.post(
            "/source-configs",
            json={
                "name": "integration-greenhouse",
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

        assert status_payload["status"] == "completed"

        events_response = client.get(f"/runs/{run_id}/events")
        assert events_response.status_code == 200
        event_types = [entry["event_type"] for entry in events_response.json()]
        assert "run.created" in event_types
        assert "run.completed" in event_types

        jobs_response = client.get(f"/jobs?run_id={run_id}")
        assert jobs_response.status_code == 200
        jobs = jobs_response.json()
        assert len(jobs) == 1
        assert jobs[0]["title"] == "Python Backend Engineer"


def test_cancel_queued_run(
    sqlite_database_url: str,
) -> None:
    """Cancel endpoint should cancel queued runs immediately."""

    app = create_app(_build_settings(sqlite_database_url, enable_worker=False))
    with TestClient(app) as client:
        run_response = client.post("/runs", json={"query": "platform"})
        assert run_response.status_code == 201
        run_id = run_response.json()["id"]

        cancel_response = client.post(f"/runs/{run_id}/cancel")
        assert cancel_response.status_code == 200
        assert cancel_response.json()["status"] == "cancelled"

        events_response = client.get(f"/runs/{run_id}/events")
        assert events_response.status_code == 200
        event_types = [entry["event_type"] for entry in events_response.json()]
        assert "run.cancelled" in event_types

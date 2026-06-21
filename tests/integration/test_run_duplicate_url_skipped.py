"""Regression test: duplicate job URLs across sources must not fail the run."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from fastapi.testclient import TestClient

from autoapply_agent.adapters.base import JobCandidate
from autoapply_agent.adapters.greenhouse import GreenhouseAdapter
from autoapply_agent.core.config import Settings
from autoapply_agent.main import create_app

if TYPE_CHECKING:
    from _pytest.monkeypatch import MonkeyPatch

_SHARED_URL = "https://boards.greenhouse.io/embed/job_board/jobs/shared-dup-001"


async def _fake_fetch_shared_url(
    self: GreenhouseAdapter,
    base_url: str,
    timeout_seconds: float,
    max_jobs: int,
) -> list[JobCandidate]:
    """Return the same canonical URL regardless of source config."""
    del self, timeout_seconds, max_jobs
    return [
        JobCandidate(
            external_id="shared-dup-001",
            title="Python Backend Engineer",
            location="Remote",
            company="example.com",
            url=_SHARED_URL,
            raw={"fixture": "duplicate-url"},
        )
    ]


def test_duplicate_url_across_sources_completes_with_one_job(
    sqlite_database_url: str,
    monkeypatch: MonkeyPatch,
) -> None:
    """Overlapping source configs returning the same URL must not raise IntegrityError."""
    monkeypatch.setattr(GreenhouseAdapter, "fetch_jobs", _fake_fetch_shared_url)

    settings = Settings(
        APP_NAME="autoapply-dedup-test",
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
        first_source = client.post(
            "/source-configs",
            json={
                "name": "integration-greenhouse-a",
                "source_type": "greenhouse",
                "base_url": "https://boards.greenhouse.io/embed/job_board?for=example-a",
            },
        )
        assert first_source.status_code == 201

        second_source = client.post(
            "/source-configs",
            json={
                "name": "integration-greenhouse-b",
                "source_type": "greenhouse",
                "base_url": "https://boards.greenhouse.io/embed/job_board?for=example-b",
            },
        )
        assert second_source.status_code == 201

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

        jobs_response = client.get(f"/jobs?run_id={run_id}")
        assert jobs_response.status_code == 200
        jobs = jobs_response.json()
        assert len(jobs) == 1
        assert jobs[0]["url"] == _SHARED_URL

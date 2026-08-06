"""Tests for jobs listing filters."""

from __future__ import annotations

import anyio
from fastapi.testclient import TestClient

from autoapply_agent.core.config import Settings
from autoapply_agent.db.models import Job, Run, RunStatus
from autoapply_agent.main import create_app


def test_list_jobs_filters_by_min_score(sqlite_database_url: str) -> None:
    """GET /jobs?min_score= must exclude jobs below the threshold."""
    settings = Settings(
        APP_NAME="autoapply-min-score-test",
        DATABASE_URL=sqlite_database_url,
        WORKER_POLL_INTERVAL_SECONDS=0.05,
        HTTP_TIMEOUT_SECONDS=0.5,
        MAX_JOBS_PER_SOURCE=5,
        HTTP_USER_AGENT="unit-test-agent",
        ENABLE_WORKER=False,
        ENVIRONMENT="test",
    )
    app = create_app(settings)
    with TestClient(app) as client:
        session_factory = app.state.session_factory

        async def _seed() -> None:
            async with session_factory() as session:
                session.add(
                    Run(
                        id="run-min-score",
                        query="python backend",
                        status=RunStatus.COMPLETED.value,
                    )
                )
                session.add_all(
                    [
                        Job(
                            run_id="run-min-score",
                            source_config_id=None,
                            external_id="low",
                            title="Low Score Role",
                            location="Remote",
                            company="Example",
                            url="https://example.com/jobs/low",
                            score=0.2,
                            plan_steps=[],
                            raw={},
                        ),
                        Job(
                            run_id="run-min-score",
                            source_config_id=None,
                            external_id="high",
                            title="High Score Role",
                            location="Remote",
                            company="Example",
                            url="https://example.com/jobs/high",
                            score=0.9,
                            plan_steps=[],
                            raw={},
                        ),
                    ]
                )
                await session.commit()

        anyio.run(_seed)

        response = client.get("/jobs", params={"run_id": "run-min-score", "min_score": 0.5})
        assert response.status_code == 200
        jobs = response.json()
        assert len(jobs) == 1
        assert jobs[0]["external_id"] == "high"
        assert jobs[0]["score"] >= 0.5

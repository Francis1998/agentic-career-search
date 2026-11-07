"""Seed a demo database through the real discovery pipeline, without network access.

``seed_demo_jobs.py`` writes hand-made rows for the search/export demo. This script
instead runs the actual :class:`~autoapply_agent.services.worker.InProcessWorker` —
deterministic scoring, priority tiers, rationale, plan steps and the ordered run
events — against an offline fixture adapter, so every job and event is exactly what a
live discovery run would store. One fixture board deliberately fails to show a
``source.failed`` event. Used by ``docs/guides/MCP_SERVER_GUIDE.md``.

Usage::

    DATABASE_URL=sqlite+aiosqlite:///$PWD/mcp-demo.db uv run python scripts/seed_mcp_demo.py

Each invocation queues and processes two more runs (``DEMO_QUERIES``) against the same
three demo sources, so running it twice simulates later runs re-capturing postings.
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Mapping, Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from autoapply_agent.adapters.base import CareerSourceAdapter, JobCandidate, SourceAdapterError
from autoapply_agent.core.config import settings
from autoapply_agent.db.base import Base
from autoapply_agent.db.models import Job, Run, RunStatus, SourceConfig, SourceType
from autoapply_agent.db.session import create_engine, create_session_factory
from autoapply_agent.services.events import append_run_event
from autoapply_agent.services.planning import DeterministicPlanningService
from autoapply_agent.services.scoring import DeterministicScoringService
from autoapply_agent.services.worker import InProcessWorker

GREENHOUSE_BOARD = "https://boards.greenhouse.io/demo"
LEVER_BOARD = "https://jobs.lever.co/demo"
WORKDAY_BOARD = "https://demo.wd1.myworkdayjobs.com/careers"

DEMO_SOURCES: tuple[tuple[str, SourceType, str], ...] = (
    ("demo-greenhouse", SourceType.GREENHOUSE, GREENHOUSE_BOARD),
    ("demo-lever", SourceType.LEVER, LEVER_BOARD),
    ("demo-workday", SourceType.WORKDAY, WORKDAY_BOARD),
)
DEMO_QUERIES: tuple[str, ...] = ("python backend remote", "platform kubernetes")


def _job(external_id: str, title: str, company: str, location: str, url: str) -> JobCandidate:
    """Build one fixture posting the way an adapter would."""

    return JobCandidate(
        external_id=external_id,
        title=title,
        location=location,
        company=company,
        url=url,
        raw={"source": "fixture"},
    )


FIXTURE_BOARDS: Mapping[str, Sequence[JobCandidate]] = {
    GREENHOUSE_BOARD: (
        _job(
            "gh-4101",
            "Senior Python Backend Engineer",
            "Acme Robotics",
            "Remote - US",
            "https://boards.greenhouse.io/acme/jobs/4101",
        ),
        _job(
            "gh-5202",
            "Staff Platform Engineer (Python, Kubernetes)",
            "Globex",
            "Anywhere",
            "https://boards.greenhouse.io/globex/jobs/5202",
        ),
        _job(
            "gh-6303",
            "Site Reliability Engineer",
            "Vandelay Industries",
            "Remote (EU)",
            "https://boards.greenhouse.io/vandelay/jobs/6303",
        ),
        _job(
            "gh-7404",
            "Data Engineer",
            "Hooli",
            "Berlin, Germany",
            "https://boards.greenhouse.io/hooli/jobs/7404",
        ),
    ),
    LEVER_BOARD: (
        # Cross-board mirror of gh-4101: search_jobs(dedupe=true) shows it once.
        _job(
            "lv-7f3c",
            "Senior Python Backend Engineer",
            "Acme Robotics, Inc.",
            "Remote - US",
            "https://jobs.lever.co/acme/7f3c-senior-python-backend",
        ),
        _job(
            "lv-piper",
            "Python Developer",
            "Pied Piper",
            "Remote",
            "https://jobs.lever.co/piedpiper/python-developer",
        ),
        _job(
            "lv-payments",
            "Backend Engineer, Payments",
            "Initech",
            "New York, NY",
            "https://jobs.lever.co/initech/payments-backend",
        ),
        _job(
            "lv-ml",
            "Machine Learning Engineer",
            "Umbrella Health",
            "Boston, MA (Hybrid)",
            "https://jobs.lever.co/umbrella/ml-engineer",
        ),
    ),
}


class FixtureBoardAdapter(CareerSourceAdapter):
    """Offline adapter serving fixed postings; unknown boards fail like an HTTP 503."""

    adapter_name = "fixture"

    def __init__(self, boards: Mapping[str, Sequence[JobCandidate]]) -> None:
        """Store the postings served per board URL."""

        self._boards = boards

    async def fetch_jobs(
        self, base_url: str, timeout_seconds: float, max_jobs: int
    ) -> list[JobCandidate]:
        """Return the board's fixture postings without any network access."""

        del timeout_seconds
        if base_url not in self._boards:
            raise SourceAdapterError(f"http error 503 for {base_url}")
        return list(self._boards[base_url])[:max_jobs]


async def _ensure_sources(session: AsyncSession) -> None:
    """Create the demo source configs that are missing."""

    for name, source_type, base_url in DEMO_SOURCES:
        existing = await session.scalar(select(SourceConfig).where(SourceConfig.name == name))
        if existing is None:
            session.add(SourceConfig(name=name, source_type=source_type.value, base_url=base_url))
    await session.commit()


async def _queue_run(session: AsyncSession, query: str) -> str:
    """Queue a run exactly like ``POST /runs`` does."""

    run = Run(id=str(uuid.uuid4()), status=RunStatus.QUEUED.value, query=query)
    session.add(run)
    await append_run_event(session, run.id, "run.created", "Run queued for processing")
    await session.commit()
    return run.id


async def _wait_until_finished(
    session_factory: async_sessionmaker[AsyncSession], run_ids: Sequence[str]
) -> None:
    """Poll until every run reached a terminal state."""

    terminal = {RunStatus.COMPLETED.value, RunStatus.FAILED.value, RunStatus.CANCELLED.value}
    for _ in range(600):
        async with session_factory() as session:
            statuses = await session.scalars(select(Run.status).where(Run.id.in_(run_ids)))
            if set(statuses) <= terminal:
                return
        await asyncio.sleep(0.05)
    raise TimeoutError("demo runs did not finish within 30 seconds")


async def seed_mcp_demo(database_url: str) -> tuple[list[str], int]:
    """Queue the demo runs and process them with the real worker.

    Args:
        database_url: SQLAlchemy async database URL.

    Returns:
        The new run ids (oldest first) and the number of jobs in the database.
    """

    engine = create_engine(database_url)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = create_session_factory(engine)
    adapter = FixtureBoardAdapter(FIXTURE_BOARDS)
    worker = InProcessWorker(
        session_factory=session_factory,
        adapters={source_type: adapter for _, source_type, _ in DEMO_SOURCES},
        scoring_service=DeterministicScoringService(),
        planning_service=DeterministicPlanningService(),
        llm_enrichment_service=None,
        poll_interval_seconds=0.05,
        default_timeout_seconds=5.0,
        max_jobs_per_source=50,
    )
    try:
        async with session_factory() as session:
            await _ensure_sources(session)
            run_ids = []
            for query in DEMO_QUERIES:
                run_ids.append(await _queue_run(session, query))
                # Distinct creation times keep the claim order (oldest first) stable.
                await asyncio.sleep(0.01)
        await worker.start()
        try:
            await _wait_until_finished(session_factory, run_ids)
        finally:
            await worker.stop()
        async with session_factory() as session:
            job_total = int(await session.scalar(select(func.count()).select_from(Job)) or 0)
    finally:
        await engine.dispose()
    return run_ids, job_total


if __name__ == "__main__":
    new_runs, jobs = asyncio.run(seed_mcp_demo(settings.database_url))
    print(f"processed {len(new_runs)} runs offline; {jobs} jobs in {settings.database_url}")
    for run_id, query in zip(new_runs, DEMO_QUERIES, strict=True):
        print(f"  run {run_id}  query={query!r}")

"""Seed a local database with demo jobs for the search, export and feed API.

Usage::

    DATABASE_URL=sqlite+aiosqlite:///./demo.db uv run python scripts/seed_demo_jobs.py

Each invocation records one completed demo run that captured the jobs below, so
running it twice simulates a second run re-capturing the same postings (try
``GET /jobs?dedupe=true``). The last row is deliberately hostile to show the CSV
formula-injection and URL hardening of ``GET /jobs/export``. Every other row carries a
short ``raw.description`` (the field a schema.org ``JobPosting`` calls ``description``)
so that ``POST /jobs/match`` has posting text to match a resume against.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from autoapply_agent.core.config import settings
from autoapply_agent.core.time import utc_now
from autoapply_agent.db.base import Base
from autoapply_agent.db.models import Job, Run, RunStatus, SourceConfig, SourceType
from autoapply_agent.db.session import create_engine, create_session_factory

DEMO_SOURCES: tuple[tuple[str, SourceType, str], ...] = (
    ("demo-greenhouse", SourceType.GREENHOUSE, "https://boards.greenhouse.io/demo"),
    ("demo-lever", SourceType.LEVER, "https://jobs.lever.co/demo"),
)

# (source index, external id, title, company, location, url, score, priority tier, hours ago)
DEMO_JOBS: tuple[tuple[int, str, str, str, str, str, float, str, int], ...] = (
    (
        0,
        "gh-4101",
        "Senior Python Engineer",
        "Acme Robotics",
        "Remote - US",
        "https://boards.greenhouse.io/acme/jobs/4101",
        0.92,
        "high",
        2,
    ),
    (
        1,
        "lv-7f3c",
        "Senior Python Engineer",
        "Acme Robotics, Inc.",
        "Remote - US",
        "https://jobs.lever.co/acme/7f3c-senior-python",
        0.9,
        "high",
        2,
    ),
    (
        0,
        "gh-5202",
        "Staff Platform Engineer (Python, Kubernetes)",
        "Globex",
        "Anywhere",
        "https://boards.greenhouse.io/globex/jobs/5202",
        0.88,
        "high",
        6,
    ),
    (
        1,
        "lv-payments",
        "Backend Engineer, Payments",
        "Initech",
        "New York, NY",
        "https://jobs.lever.co/initech/payments-backend",
        0.71,
        "medium",
        20,
    ),
    (
        0,
        "gh-6303",
        "Site Reliability Engineer",
        "Vandelay Industries",
        "Remote (EU)",
        "https://boards.greenhouse.io/vandelay/jobs/6303",
        0.66,
        "medium",
        30,
    ),
    (
        1,
        "lv-ml",
        "Machine Learning Engineer",
        "Umbrella Health",
        "Boston, MA (Hybrid)",
        "https://jobs.lever.co/umbrella/ml-engineer",
        0.62,
        "medium",
        50,
    ),
    (
        0,
        "gh-7404",
        "Data Engineer",
        "Hooli",
        "Berlin, Germany",
        "https://boards.greenhouse.io/hooli/jobs/7404",
        0.55,
        "low",
        70,
    ),
    (
        1,
        "lv-inject",
        '=HYPERLINK("https://evil.example","Apply here")',
        "Injected Co",
        "-1+1",
        "javascript:alert(1)",
        0.31,
        "low",
        90,
    ),
)

_ACME_DESCRIPTION = (
    "Build the fleet telemetry backend in Python with FastAPI and PostgreSQL. Ship services "
    "on AWS with Docker and Kubernetes, CI/CD in GitHub Actions. Nice to have: Go, Kafka."
)
# External id -> raw.description (the hostile row has none).
DEMO_DESCRIPTIONS: dict[str, str] = {
    "gh-4101": _ACME_DESCRIPTION,
    "lv-7f3c": _ACME_DESCRIPTION,
    "gh-5202": (
        "Own the internal developer platform: Kubernetes (EKS), Terraform, Helm and Argo CD "
        "on AWS. Write Python and Go tooling, run observability with Prometheus and Grafana "
        "and lead system design reviews."
    ),
    "lv-payments": (
        "Design payment APIs in Java and Spring Boot on PostgreSQL and Kafka. You know "
        "microservices, distributed systems and PCI DSS."
    ),
    "gh-6303": (
        "Keep production healthy on Linux and Kubernetes with Terraform, Prometheus and "
        "Grafana; join the incident response rotation. Automate in Python or Bash."
    ),
    "lv-ml": (
        "Train and ship models with PyTorch and scikit-learn; MLOps with MLflow and Docker on "
        "AWS SageMaker. Strong SQL and statistics."
    ),
    "gh-7404": (
        "Build batch and streaming pipelines with Spark, Airflow, dbt and Kafka on GCP "
        "(BigQuery). SQL and Python required."
    ),
}


async def _demo_sources(session: AsyncSession) -> list[SourceConfig]:
    """Return the demo source configs, creating any that are missing."""

    sources: list[SourceConfig] = []
    for name, source_type, base_url in DEMO_SOURCES:
        source = await session.scalar(select(SourceConfig).where(SourceConfig.name == name))
        if source is None:
            source = SourceConfig(name=name, source_type=source_type.value, base_url=base_url)
            session.add(source)
            await session.flush()
        sources.append(source)
    return sources


async def seed_demo_jobs() -> tuple[str, int]:
    """Insert one completed demo run with its captured jobs.

    Returns:
        The new run id and the number of jobs inserted.
    """

    engine = create_engine(settings.database_url)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    now = utc_now()
    run = Run(
        id=str(uuid.uuid4()),
        status=RunStatus.COMPLETED.value,
        query="python backend remote",
        started_at=now,
        finished_at=now,
    )
    async with create_session_factory(engine)() as session:
        sources = await _demo_sources(session)
        session.add(run)
        for index, external_id, title, company, location, url, score, tier, hours_ago in DEMO_JOBS:
            source = sources[index]
            raw: dict[str, object] = {
                "source": source.source_type,
                "agent_decision": {"priority_tier": tier},
            }
            if external_id in DEMO_DESCRIPTIONS:
                raw["description"] = DEMO_DESCRIPTIONS[external_id]
            session.add(
                Job(
                    run_id=run.id,
                    source_config_id=source.id,
                    external_id=external_id,
                    title=title,
                    location=location,
                    company=company,
                    url=url,
                    score=score,
                    plan_steps=["Review fit with the decision trace", "Tailor resume bullets"],
                    raw=raw,
                    created_at=now - timedelta(hours=hours_ago),
                )
            )
        await session.commit()
    await engine.dispose()
    return run.id, len(DEMO_JOBS)


if __name__ == "__main__":
    run_id, count = asyncio.run(seed_demo_jobs())
    print(f"seeded {count} jobs (run {run_id}) into {settings.database_url}")

"""Schema tests: job ordering indexes exist and back the keyset export batches."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine as create_sync_engine
from sqlalchemy import event, inspect

from alembic import command
from autoapply_agent.db.base import Base
from autoapply_agent.db.models import Job, Run, RunStatus
from autoapply_agent.db.session import create_engine, create_session_factory
from autoapply_agent.services.job_search import JobSearchFilters, JobSort, iter_jobs

REPO_ROOT = Path(__file__).resolve().parents[2]
ORDERING_INDEXES = {
    "ix_jobs_created_at_id": ["created_at", "id"],
    "ix_jobs_score_created_at_id": ["score", "created_at", "id"],
}


def _job_indexes(database_url: str) -> dict[str, list[str]]:
    """Return ``{index name: columns}`` for the jobs table of a sync database URL."""

    engine = create_sync_engine(database_url)
    try:
        return {
            str(index["name"]): [str(column) for column in index["column_names"]]
            for index in inspect(engine).get_indexes("jobs")
        }
    finally:
        engine.dispose()


def _alembic_config(database_url: str) -> Config:
    """Build an Alembic config without ``alembic.ini`` (keeps pytest logging intact)."""

    config = Config()
    config.set_main_option("script_location", str(REPO_ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


async def test_create_all_creates_the_ordering_indexes(tmp_path: Path) -> None:
    """``Base.metadata.create_all`` (used at app startup) declares both indexes."""

    db_path = tmp_path / "create_all.db"
    engine = create_engine(f"sqlite+aiosqlite:///{db_path}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    await engine.dispose()

    indexes = _job_indexes(f"sqlite:///{db_path}")

    assert {name: indexes.get(name) for name in ORDERING_INDEXES} == ORDERING_INDEXES


def test_alembic_head_matches_models_and_downgrades(tmp_path: Path) -> None:
    """Migrations create the indexes, match model metadata, and downgrade cleanly."""

    database_url = f"sqlite:///{tmp_path / 'alembic.db'}"
    config = _alembic_config(database_url)

    command.upgrade(config, "head")
    upgraded = _job_indexes(database_url)
    engine = create_sync_engine(database_url)
    try:
        with engine.connect() as connection:
            diff = compare_metadata(MigrationContext.configure(connection), Base.metadata)
    finally:
        engine.dispose()
    command.downgrade(config, "-1")
    downgraded = _job_indexes(database_url)

    assert {name: upgraded.get(name) for name in ORDERING_INDEXES} == ORDERING_INDEXES
    assert [entry for entry in diff if "index" in str(entry[0])] == []
    assert not set(ORDERING_INDEXES) & set(downgraded)
    assert "ix_jobs_run_id" in downgraded


@pytest.mark.parametrize(
    ("sort", "index_name"),
    [
        (JobSort.NEWEST, "ix_jobs_created_at_id"),
        (JobSort.SCORE, "ix_jobs_score_created_at_id"),
    ],
)
async def test_keyset_batches_seek_through_the_ordering_index(
    tmp_path: Path, sort: JobSort, index_name: str
) -> None:
    """SQLite plans every export batch as an index seek, never a temp-B-tree sort."""

    engine = create_engine(f"sqlite+aiosqlite:///{tmp_path / 'plan.db'}")
    batches: list[tuple[str, Any]] = []

    def capture(*args: Any) -> None:
        statement, parameters = args[2], args[3]
        if statement.lstrip().startswith("SELECT") and "LIMIT" in statement:
            batches.append((statement, parameters))

    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with create_session_factory(engine)() as session:
            session.add(Run(id="run-plan", status=RunStatus.COMPLETED.value))
            session.add_all(
                Job(
                    run_id="run-plan",
                    title=f"Engineer {index}",
                    url=f"https://jobs.example.com/plan/{index}",
                    score=index % 7 / 10,
                    plan_steps=[],
                )
                for index in range(1_100)
            )
            await session.commit()

        event.listen(engine.sync_engine, "before_cursor_execute", capture)
        async with create_session_factory(engine)() as session:
            exported = [job async for job in iter_jobs(session, JobSearchFilters(sort=sort))]
        event.remove(engine.sync_engine, "before_cursor_execute", capture)

        plans: list[str] = []
        async with engine.connect() as connection:
            for statement, parameters in batches:
                result = await connection.exec_driver_sql(
                    f"EXPLAIN QUERY PLAN {statement}", parameters
                )
                plans.append(" / ".join(str(row[-1]) for row in result))
    finally:
        await engine.dispose()

    assert len(exported) == 1_100
    assert len(batches) == 3
    for plan in plans:
        assert index_name in plan, plan
        assert "TEMP B-TREE" not in plan, plan
    assert all(plan.startswith("SEARCH") for plan in plans[1:]), plans

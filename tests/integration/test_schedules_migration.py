"""Alembic migration f5c8a2d71b39: run schedule tables upgrade and downgrade."""

from __future__ import annotations

from pathlib import Path

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine as create_sync_engine
from sqlalchemy import inspect

from alembic import command
from autoapply_agent.db.base import Base
from autoapply_agent.db.session import create_engine
from tests.integration.test_applications_migration import _schema
from tests.integration.test_jobs_schema_indexes import _alembic_config

SCHEDULE_TABLES = {"run_schedules", "run_schedule_events"}
PREVIOUS_HEAD = "e5b8c2a7f913"


def _schedule_diff(database_url: str) -> list[object]:
    """Autogenerate differences between the database and the models for schedule tables."""

    engine = create_sync_engine(database_url)
    try:
        with engine.connect() as connection:
            diff = compare_metadata(MigrationContext.configure(connection), Base.metadata)
    finally:
        engine.dispose()
    return [entry for entry in diff if any(table in str(entry) for table in SCHEDULE_TABLES)]


def _indexes(database_url: str, table: str) -> set[str]:
    engine = create_sync_engine(database_url)
    try:
        return {str(index["name"]) for index in inspect(engine).get_indexes(table)}
    finally:
        engine.dispose()


def test_migrations_have_a_single_head(tmp_path: Path) -> None:
    script = ScriptDirectory.from_config(_alembic_config(f"sqlite:///{tmp_path / 'heads.db'}"))

    assert len(script.get_heads()) == 1


def test_upgrade_creates_the_schedule_tables_matching_the_models(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'schedules.db'}"

    command.upgrade(_alembic_config(database_url), "head")

    schema = _schema(database_url)
    assert SCHEDULE_TABLES <= set(schema)
    assert {
        "name",
        "kind",
        "interval_minutes",
        "cron",
        "timezone",
        "overlap_policy",
        "jitter_seconds",
        "paused",
        "pause_note",
        "next_run_at",
        "buffered_at",
        "last_fired_at",
        "last_run_id",
    } <= schema["run_schedules"]
    assert {"schedule_id", "kind", "run_id", "scheduled_for", "reason", "details"} <= schema[
        "run_schedule_events"
    ]
    assert "ix_run_schedules_next_run_at" in _indexes(database_url, "run_schedules")
    assert _schedule_diff(database_url) == []


def test_downgrade_drops_only_the_schedule_tables_and_upgrade_is_repeatable(
    tmp_path: Path,
) -> None:
    database_url = f"sqlite:///{tmp_path / 'schedules.db'}"
    config = _alembic_config(database_url)
    command.upgrade(config, "head")

    command.downgrade(config, PREVIOUS_HEAD)
    downgraded = _schema(database_url)
    command.upgrade(config, "head")

    assert not SCHEDULE_TABLES & set(downgraded)
    assert {"jobs", "runs", "applications", "application_events"} <= set(downgraded)
    assert SCHEDULE_TABLES <= set(_schema(database_url))


async def test_app_created_database_upgrades_after_stamping_the_baseline(tmp_path: Path) -> None:
    db_path = tmp_path / "app.db"
    engine = create_engine(f"sqlite+aiosqlite:///{db_path}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    await engine.dispose()
    config = _alembic_config(f"sqlite:///{db_path}")

    command.stamp(config, "87de9ef55524")
    command.upgrade(config, "head")

    assert _schedule_diff(f"sqlite:///{db_path}") == []

"""Alembic migration d3a9f1c4b7e2: application tracker tables upgrade and downgrade."""

from __future__ import annotations

from pathlib import Path

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine as create_sync_engine
from sqlalchemy import inspect

from alembic import command
from autoapply_agent.db.base import Base
from tests.integration.test_jobs_schema_indexes import _alembic_config

TRACKER_TABLES = {"applications", "application_events"}
PREVIOUS_HEAD = "c41f2a7d9e60"


def _schema(database_url: str) -> dict[str, set[str]]:
    """Return ``{table: column names}`` of a sync database URL."""

    engine = create_sync_engine(database_url)
    try:
        inspector = inspect(engine)
        return {
            table: {str(column["name"]) for column in inspector.get_columns(table)}
            for table in inspector.get_table_names()
        }
    finally:
        engine.dispose()


def _tracker_diff(database_url: str) -> list[object]:
    """Autogenerate differences between the database and the models for tracker tables."""

    engine = create_sync_engine(database_url)
    try:
        with engine.connect() as connection:
            diff = compare_metadata(MigrationContext.configure(connection), Base.metadata)
    finally:
        engine.dispose()
    return [entry for entry in diff if any(table in str(entry) for table in TRACKER_TABLES)]


def test_upgrade_creates_the_tracker_tables_matching_the_models(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'tracker.db'}"
    config = _alembic_config(database_url)

    command.upgrade(config, "head")

    schema = _schema(database_url)
    assert TRACKER_TABLES <= set(schema)
    assert {"job_id", "stage", "notes", "applied_at", "next_action_at", "archived"} <= schema[
        "applications"
    ]
    assert {"application_id", "sequence", "event_type", "from_stage", "to_stage"} <= schema[
        "application_events"
    ]
    assert _tracker_diff(database_url) == []


def test_downgrade_drops_only_the_tracker_tables_and_upgrade_is_repeatable(
    tmp_path: Path,
) -> None:
    database_url = f"sqlite:///{tmp_path / 'tracker.db'}"
    config = _alembic_config(database_url)
    command.upgrade(config, "head")

    command.downgrade(config, PREVIOUS_HEAD)
    downgraded = _schema(database_url)
    command.upgrade(config, "head")

    assert not TRACKER_TABLES & set(downgraded)
    assert {"jobs", "runs", "run_events", "source_configs"} <= set(downgraded)
    assert TRACKER_TABLES <= set(_schema(database_url))

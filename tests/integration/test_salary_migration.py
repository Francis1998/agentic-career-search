"""Alembic migration e5b8c2a7f913: job salary columns upgrade, downgrade and idempotency."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine as create_sync_engine
from sqlalchemy import inspect

from alembic import command
from autoapply_agent.db.base import Base
from tests.integration.test_jobs_schema_indexes import _alembic_config

SALARY_COLUMNS = {"salary_min_annual", "salary_max_annual", "salary_currency", "salary_interval"}
SALARY_INDEX = "ix_jobs_salary_currency_max_annual_created_at_id"
PREVIOUS_HEAD = "d3a9f1c4b7e2"


def _jobs_schema(database_url: str) -> tuple[set[str], set[str]]:
    """Return the column and index names of ``jobs``."""

    engine = create_sync_engine(database_url)
    try:
        inspector = inspect(engine)
        columns = {str(column["name"]) for column in inspector.get_columns("jobs")}
        indexes = {str(index["name"]) for index in inspector.get_indexes("jobs")}
    finally:
        engine.dispose()
    return columns, indexes


def _salary_diff(database_url: str) -> list[object]:
    """Autogenerate differences between the database and the models for the pay schema."""

    engine = create_sync_engine(database_url)
    try:
        with engine.connect() as connection:
            diff = compare_metadata(MigrationContext.configure(connection), Base.metadata)
    finally:
        engine.dispose()
    return [entry for entry in diff if "salary" in str(entry)]


def test_there_is_exactly_one_head(tmp_path: Path) -> None:
    script = ScriptDirectory.from_config(_alembic_config(f"sqlite:///{tmp_path / 'x.db'}"))

    assert script.get_heads() == ["e5b8c2a7f913"]


def test_upgrade_adds_the_indexed_salary_columns_matching_the_models(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'salary.db'}"

    command.upgrade(_alembic_config(database_url), "head")

    columns, indexes = _jobs_schema(database_url)
    assert SALARY_COLUMNS <= columns
    assert SALARY_INDEX in indexes
    assert _salary_diff(database_url) == []


def test_downgrade_drops_only_the_salary_schema_and_keeps_rows(tmp_path: Path) -> None:
    db_path = tmp_path / "salary.db"
    database_url = f"sqlite:///{db_path}"
    config = _alembic_config(database_url)
    command.upgrade(config, "head")
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            "INSERT INTO runs (id, status, cancel_requested, created_at, "
            "updated_at) VALUES ('r', 'completed', 0, '2026-11-27', '2026-11-27')"
        )
        connection.execute(
            "INSERT INTO jobs (run_id, title, url, score, plan_steps, created_at, "
            "salary_min_annual, salary_max_annual, salary_currency, salary_interval) VALUES "
            "('r', 'Engineer', 'https://x.test/1', 0.5, '[]', '2026-11-27', 1, 2, 'USD', 'year')"
        )

    command.downgrade(config, PREVIOUS_HEAD)
    columns, indexes = _jobs_schema(database_url)
    with sqlite3.connect(db_path) as connection:
        titles = connection.execute("SELECT title FROM jobs").fetchall()
    command.upgrade(config, "head")

    assert not SALARY_COLUMNS & columns
    assert {"title", "url", "score", "raw", "created_at"} <= columns
    assert SALARY_INDEX not in indexes
    assert {"ix_jobs_created_at_id", "ix_jobs_score_created_at_id", "ix_jobs_run_id"} <= indexes
    assert titles == [("Engineer",)]
    assert SALARY_COLUMNS <= _jobs_schema(database_url)[0]

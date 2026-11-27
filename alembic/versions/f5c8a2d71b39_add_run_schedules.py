"""add run schedules and their history

Revision ID: f5c8a2d71b39
Revises: e5b8c2a7f913
Create Date: 2026-11-27 12:20:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "f5c8a2d71b39"
down_revision = "e5b8c2a7f913"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create ``run_schedules`` and the append-only ``run_schedule_events`` history.

    Idempotent: databases created by the app's ``create_all`` (then stamped at the
    initial revision) may already have these tables.
    """

    op.create_table(
        "run_schedules",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("query", sa.String(length=256), nullable=True),
        sa.Column("source_config_ids", sa.JSON(), nullable=True),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("interval_minutes", sa.Integer(), nullable=True),
        sa.Column("cron", sa.String(length=120), nullable=True),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("overlap_policy", sa.String(length=16), nullable=False),
        sa.Column("jitter_seconds", sa.Integer(), nullable=False),
        sa.Column("paused", sa.Boolean(), nullable=False),
        sa.Column("pause_note", sa.String(length=500), nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("buffered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_fired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_run_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["last_run_id"], ["runs.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_run_schedules_name"),
        if_not_exists=True,
    )
    op.create_index(
        "ix_run_schedules_next_run_at",
        "run_schedules",
        ["next_run_at"],
        unique=False,
        if_not_exists=True,
    )
    op.create_table(
        "run_schedule_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("schedule_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=24), nullable=False),
        sa.Column("run_id", sa.String(length=36), nullable=True),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reason", sa.String(length=512), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"]),
        sa.ForeignKeyConstraint(["schedule_id"], ["run_schedules.id"]),
        sa.PrimaryKeyConstraint("id"),
        if_not_exists=True,
    )
    op.create_index(
        "ix_run_schedule_events_schedule_id_id",
        "run_schedule_events",
        ["schedule_id", "id"],
        unique=False,
        if_not_exists=True,
    )


def downgrade() -> None:
    """Drop the schedule tables (schedules and their history are lost; runs stay)."""

    op.drop_index(
        "ix_run_schedule_events_schedule_id_id",
        table_name="run_schedule_events",
        if_exists=True,
    )
    op.drop_table("run_schedule_events", if_exists=True)
    op.drop_index("ix_run_schedules_next_run_at", table_name="run_schedules", if_exists=True)
    op.drop_table("run_schedules", if_exists=True)

"""add application tracker tables

Revision ID: d3a9f1c4b7e2
Revises: c41f2a7d9e60
Create Date: 2026-11-19 11:40:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "d3a9f1c4b7e2"
down_revision = "c41f2a7d9e60"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create ``applications`` and the append-only ``application_events`` history.

    Idempotent: databases created by the app's ``create_all`` (then stamped at the
    initial revision) may already have these tables.
    """

    op.create_table(
        "applications",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("stage", sa.String(length=16), nullable=False),
        sa.Column("archived", sa.Boolean(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_action_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_action", sa.String(length=200), nullable=True),
        sa.Column("stage_changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id", name="uq_applications_job_id"),
        if_not_exists=True,
    )
    op.create_index(
        "ix_applications_next_action_at",
        "applications",
        ["next_action_at"],
        unique=False,
        if_not_exists=True,
    )
    op.create_table(
        "application_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("application_id", sa.Integer(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("from_stage", sa.String(length=16), nullable=True),
        sa.Column("to_stage", sa.String(length=16), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("changes", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "application_id", "sequence", name="uq_application_events_application_sequence"
        ),
        if_not_exists=True,
    )


def downgrade() -> None:
    """Drop the application tracker tables (their data is lost)."""

    op.drop_table("application_events", if_exists=True)
    op.drop_index("ix_applications_next_action_at", table_name="applications", if_exists=True)
    op.drop_table("applications", if_exists=True)

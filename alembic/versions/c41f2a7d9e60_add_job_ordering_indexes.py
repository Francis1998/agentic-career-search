"""add job ordering indexes

Revision ID: c41f2a7d9e60
Revises: 87de9ef55524
Create Date: 2026-11-06 23:58:00.000000
"""

from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "c41f2a7d9e60"
down_revision = "87de9ef55524"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Index the job search orderings used by list, export and feed queries.

    Idempotent: databases created by the app's ``create_all`` (then stamped at the
    initial revision) may already have these indexes.
    """

    op.create_index(
        "ix_jobs_created_at_id", "jobs", ["created_at", "id"], unique=False, if_not_exists=True
    )
    op.create_index(
        "ix_jobs_score_created_at_id",
        "jobs",
        ["score", "created_at", "id"],
        unique=False,
        if_not_exists=True,
    )


def downgrade() -> None:
    """Drop the job ordering indexes."""

    op.drop_index("ix_jobs_score_created_at_id", table_name="jobs", if_exists=True)
    op.drop_index("ix_jobs_created_at_id", table_name="jobs", if_exists=True)

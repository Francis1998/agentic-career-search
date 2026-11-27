"""add job salary columns

Revision ID: e5b8c2a7f913
Revises: d3a9f1c4b7e2
Create Date: 2026-11-27 12:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "e5b8c2a7f913"
down_revision = "d3a9f1c4b7e2"
branch_labels = None
depends_on = None

SALARY_COLUMNS: tuple[tuple[str, sa.types.TypeEngine[object]], ...] = (
    ("salary_min_annual", sa.BigInteger()),
    ("salary_max_annual", sa.BigInteger()),
    ("salary_currency", sa.String(length=3)),
    ("salary_interval", sa.String(length=8)),
)
SALARY_INDEX = "ix_jobs_salary_currency_max_annual_created_at_id"


def upgrade() -> None:
    """Add the nullable, indexed pay columns to ``jobs`` (existing rows stay NULL).

    Idempotent: databases created by the app's ``create_all`` (then stamped at the
    initial revision) may already have these columns and the index. Jobs captured
    before this revision get pay only when discovery captures them again.
    """

    existing = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("jobs")}
    for name, column_type in SALARY_COLUMNS:
        if name not in existing:
            op.add_column("jobs", sa.Column(name, column_type, nullable=True))
    op.create_index(
        SALARY_INDEX,
        "jobs",
        ["salary_currency", "salary_max_annual", "created_at", "id"],
        unique=False,
        if_not_exists=True,
    )


def downgrade() -> None:
    """Drop the pay columns and their index (captured pay stays in ``raw``)."""

    op.drop_index(SALARY_INDEX, table_name="jobs", if_exists=True)
    existing = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("jobs")}
    with op.batch_alter_table("jobs") as batch_op:
        for name, _ in reversed(SALARY_COLUMNS):
            if name in existing:
                batch_op.drop_column(name)

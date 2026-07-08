"""Seed script for local source configuration records."""

from __future__ import annotations

import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from autoapply_agent.core.config import settings
from autoapply_agent.db.models import SourceConfig, SourceType
from autoapply_agent.db.session import create_engine, create_session_factory


async def seed_source_configs() -> None:
    """Insert sample source configs for local development."""

    engine = create_engine(settings.database_url)
    session_factory = create_session_factory(engine)

    async with session_factory() as session:
        await _insert_defaults(session)
        await session.commit()

    await engine.dispose()


async def _insert_defaults(session: AsyncSession) -> None:
    """Insert deterministic default source rows.

    Args:
        session: Active async session.
    """

    session.add_all(
        [
            SourceConfig(
                name="example-greenhouse",
                source_type=SourceType.GREENHOUSE.value,
                base_url="https://boards.greenhouse.io/embed/job_board?for=example",
                enabled=True,
            ),
            SourceConfig(
                name="example-lever",
                source_type=SourceType.LEVER.value,
                base_url="https://jobs.lever.co/example",
                enabled=True,
            ),
            SourceConfig(
                name="example-workable",
                source_type=SourceType.WORKABLE.value,
                base_url="https://apply.workable.com/example",
                enabled=True,
            ),
            SourceConfig(
                name="example-recruitee",
                source_type=SourceType.RECRUITEE.value,
                base_url="https://example.recruitee.com",
                enabled=True,
            ),
        ]
    )


if __name__ == "__main__":
    asyncio.run(seed_source_configs())

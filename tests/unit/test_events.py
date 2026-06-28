"""Unit tests for run event sequencing."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from autoapply_agent.db.base import Base
from autoapply_agent.db.models import Run, RunEvent, RunStatus
from autoapply_agent.services.events import append_run_event


@asynccontextmanager
async def _event_session(sqlite_database_url: str) -> AsyncIterator[AsyncSession]:
    """Create an isolated database session for event tests.

    Args:
        sqlite_database_url: Async sqlite database URL.

    Yields:
        SQLAlchemy async session with all tables created.
    """

    engine = create_async_engine(sqlite_database_url)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            yield session
    finally:
        await engine.dispose()


async def _create_run(session: AsyncSession, run_id: str) -> None:
    """Persist a minimal run row for event foreign keys.

    Args:
        session: Active async DB session.
        run_id: Run identifier to persist.
    """

    session.add(Run(id=run_id, status=RunStatus.QUEUED.value, query="python agent"))
    await session.flush()


async def test_append_run_event_starts_sequence_at_one(sqlite_database_url: str) -> None:
    """First event for a run should use sequence one."""

    async with _event_session(sqlite_database_url) as session:
        await _create_run(session, "run-1")

        run_event = await append_run_event(
            session=session,
            run_id="run-1",
            event_type="run.created",
            message="Run created",
            payload={"source": "unit"},
        )

        assert run_event.sequence == 1
        assert run_event.payload == {"source": "unit"}


async def test_append_run_event_increments_monotonically(
    sqlite_database_url: str,
) -> None:
    """Successive events for a run should receive increasing sequences."""

    async with _event_session(sqlite_database_url) as session:
        await _create_run(session, "run-1")

        await append_run_event(session, "run-1", "run.created", "Run created")
        await append_run_event(
            session,
            "run-1",
            "agent.decision",
            "Decision captured",
            {"priority_tier": "high"},
        )
        await append_run_event(session, "run-1", "run.completed", "Run completed")

        result = await session.scalars(
            select(RunEvent).where(RunEvent.run_id == "run-1").order_by(RunEvent.sequence)
        )
        events = list(result)

        assert [event.sequence for event in events] == [1, 2, 3]
        assert [event.event_type for event in events] == [
            "run.created",
            "agent.decision",
            "run.completed",
        ]
        assert events[1].payload == {"priority_tier": "high"}


async def test_append_run_event_sequences_are_per_run(sqlite_database_url: str) -> None:
    """Event sequences should be independent for each run."""

    async with _event_session(sqlite_database_url) as session:
        await _create_run(session, "run-1")
        await _create_run(session, "run-2")

        first_run_event = await append_run_event(
            session,
            "run-1",
            "run.created",
            "First run created",
        )
        second_run_event = await append_run_event(
            session,
            "run-2",
            "run.created",
            "Second run created",
        )
        next_first_run_event = await append_run_event(
            session,
            "run-1",
            "run.started",
            "First run started",
        )

        assert first_run_event.sequence == 1
        assert second_run_event.sequence == 1
        assert next_first_run_event.sequence == 2

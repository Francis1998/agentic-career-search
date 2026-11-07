"""Read-only queries over runs, run events and source configs.

Shared by the HTTP routes and the read-only MCP server (:mod:`autoapply_agent.mcp`),
so both surfaces list and order these records the same way. Nothing here writes.
"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from autoapply_agent.db.models import Job, Run, RunEvent, SourceConfig


async def list_runs(
    session: AsyncSession,
    *,
    status: str | None = None,
    limit: int,
    offset: int = 0,
) -> tuple[int, list[Run]]:
    """Return one page of runs, newest first, plus the total number of matches.

    Args:
        session: Active async DB session.
        status: Optional run status to keep (see :class:`~autoapply_agent.db.models.RunStatus`).
        limit: Maximum number of runs in the page.
        offset: Number of matches to skip.

    Returns:
        ``(total, runs)`` ordered by creation time, then id, descending.
    """

    conditions = [Run.status == status] if status is not None else []
    total = await session.scalar(select(func.count()).select_from(Run).where(*conditions))
    rows = await session.scalars(
        select(Run)
        .where(*conditions)
        .order_by(Run.created_at.desc(), Run.id.desc())
        .offset(offset)
        .limit(limit)
    )
    return int(total or 0), list(rows)


async def run_events(
    session: AsyncSession, run_id: str, *, limit: int | None = None
) -> list[RunEvent]:
    """Return a run's events in sequence order.

    Args:
        session: Active async DB session.
        run_id: Run identifier.
        limit: Optional maximum; keeps the most recent events.

    Returns:
        Events ordered by ascending ``sequence``.
    """

    statement = select(RunEvent).where(RunEvent.run_id == run_id)
    if limit is None:
        return list(await session.scalars(statement.order_by(RunEvent.sequence.asc())))
    recent = await session.scalars(statement.order_by(RunEvent.sequence.desc()).limit(limit))
    return list(recent)[::-1]


async def count_run_events(session: AsyncSession, run_id: str) -> int:
    """Return how many events a run has recorded.

    Args:
        session: Active async DB session.
        run_id: Run identifier.

    Returns:
        Number of persisted events.
    """

    total = await session.scalar(
        select(func.count()).select_from(RunEvent).where(RunEvent.run_id == run_id)
    )
    return int(total or 0)


async def job_counts_by_run(session: AsyncSession, run_ids: Sequence[str]) -> dict[str, int]:
    """Count the jobs each run captured.

    Args:
        session: Active async DB session.
        run_ids: Runs to count; runs without jobs are omitted from the result.

    Returns:
        Mapping of run id to captured job count.
    """

    if not run_ids:
        return {}
    rows = await session.execute(
        select(Job.run_id, func.count()).where(Job.run_id.in_(run_ids)).group_by(Job.run_id)
    )
    return {run_id: int(count) for run_id, count in rows.tuples()}


async def list_source_configs(
    session: AsyncSession, *, enabled: bool | None = None
) -> list[SourceConfig]:
    """Return source configs ordered by id.

    Args:
        session: Active async DB session.
        enabled: ``True``/``False`` keeps only enabled/disabled configs; None keeps all.

    Returns:
        Source configs.
    """

    statement = select(SourceConfig).order_by(SourceConfig.id.asc())
    if enabled is not None:
        statement = statement.where(SourceConfig.enabled.is_(enabled))
    return list(await session.scalars(statement))


async def job_counts_by_source(session: AsyncSession) -> dict[int, int]:
    """Count the jobs captured from each source config.

    Args:
        session: Active async DB session.

    Returns:
        Mapping of source config id to captured job count.
    """

    rows = await session.execute(
        select(Job.source_config_id, func.count())
        .where(Job.source_config_id.is_not(None))
        .group_by(Job.source_config_id)
    )
    return {source_id: int(count) for source_id, count in rows.tuples() if source_id is not None}

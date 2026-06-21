"""Run event persistence helpers."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from autoapply_agent.db.models import RunEvent


async def append_run_event(
    session: AsyncSession,
    run_id: str,
    event_type: str,
    message: str,
    payload: dict[str, object] | None = None,
) -> RunEvent:
    """Persist a run event with monotonically increasing sequence.

    Args:
        session: Active async DB session.
        run_id: Run identifier.
        event_type: Event type key.
        message: Human-readable message.
        payload: Optional event payload dictionary.

    Returns:
        Persisted run event instance.
    """

    sequence_query = select(func.coalesce(func.max(RunEvent.sequence), 0)).where(
        RunEvent.run_id == run_id
    )
    current_max = await session.scalar(sequence_query)
    next_sequence = int(current_max or 0) + 1

    run_event = RunEvent(
        run_id=run_id,
        sequence=next_sequence,
        event_type=event_type,
        message=message,
        payload=payload,
    )
    session.add(run_event)
    await session.flush()
    return run_event

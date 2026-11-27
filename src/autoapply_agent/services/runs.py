"""Queue discovery runs: the one code path behind ``POST /runs`` and run schedules."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from autoapply_agent.db.models import Run, RunStatus
from autoapply_agent.services.events import append_run_event

RUN_CREATED_MESSAGE = "Run queued for processing"


async def enqueue_run(
    session: AsyncSession,
    *,
    query: str | None,
    source_config_ids: list[int] | None,
    message: str = RUN_CREATED_MESSAGE,
    payload: dict[str, object] | None = None,
) -> Run:
    """Add a queued run and its ``run.created`` event to the session (not committed).

    The in-process worker picks the run up like any other queued run.

    Args:
        session: Active async DB session; the caller commits.
        query: Optional query terms the decision engine scores against.
        source_config_ids: Source configs to process (``None`` or empty: every enabled one).
        message: ``run.created`` event message.
        payload: Optional ``run.created`` event payload.

    Returns:
        The pending run.
    """

    run = Run(
        id=str(uuid.uuid4()),
        status=RunStatus.QUEUED.value,
        query=query,
        source_config_ids=list(source_config_ids) if source_config_ids is not None else None,
    )
    session.add(run)
    await append_run_event(session, run.id, "run.created", message, payload=payload)
    return run

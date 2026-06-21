"""Run lifecycle routes."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from autoapply_agent.api.deps import get_session
from autoapply_agent.core.time import utc_now
from autoapply_agent.db.models import Run, RunEvent, RunStatus
from autoapply_agent.schemas.runs import RunCreate, RunEventRead, RunRead
from autoapply_agent.services.events import append_run_event

router = APIRouter(prefix="/runs", tags=["runs"])


@router.post("", response_model=RunRead, status_code=status.HTTP_201_CREATED)
async def create_run(payload: RunCreate, session: AsyncSession = Depends(get_session)) -> Run:
    """Queue a new run for worker processing.

    Args:
        payload: Run creation payload.
        session: Request-scoped async session.

    Returns:
        Created queued run.
    """

    run = Run(
        id=str(uuid.uuid4()),
        status=RunStatus.QUEUED.value,
        query=payload.query,
        source_config_ids=payload.source_config_ids,
    )
    session.add(run)
    await append_run_event(session, run.id, "run.created", "Run queued for processing")
    await session.commit()
    await session.refresh(run)
    return run


@router.get("/{run_id}", response_model=RunRead)
async def get_run(run_id: str, session: AsyncSession = Depends(get_session)) -> Run:
    """Get run status by id.

    Args:
        run_id: Run identifier.
        session: Request-scoped async session.

    Returns:
        Run model.
    """

    run = await session.get(Run, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="run not found")
    return run


@router.get("/{run_id}/events", response_model=list[RunEventRead])
async def get_run_events(
    run_id: str, session: AsyncSession = Depends(get_session)
) -> list[RunEvent]:
    """List persisted run events.

    Args:
        run_id: Run identifier.
        session: Request-scoped async session.

    Returns:
        Ordered run events list.
    """

    run = await session.get(Run, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="run not found")

    events = await session.scalars(
        select(RunEvent).where(RunEvent.run_id == run_id).order_by(RunEvent.sequence.asc())
    )
    return list(events)


@router.post("/{run_id}/cancel", response_model=RunRead)
async def cancel_run(run_id: str, session: AsyncSession = Depends(get_session)) -> Run:
    """Request cancellation for queued or running run.

    Args:
        run_id: Run identifier.
        session: Request-scoped async session.

    Returns:
        Updated run model.
    """

    run = await session.get(Run, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="run not found")

    terminal_states = {RunStatus.COMPLETED.value, RunStatus.CANCELLED.value, RunStatus.FAILED.value}
    if run.status in terminal_states:
        await append_run_event(
            session,
            run.id,
            "run.cancel_ignored",
            "Cancel request ignored due to terminal run state",
        )
        await session.commit()
        await session.refresh(run)
        return run

    run.cancel_requested = True
    if run.status == RunStatus.QUEUED.value:
        run.status = RunStatus.CANCELLED.value
        run.finished_at = utc_now()
        await append_run_event(session, run.id, "run.cancelled", "Run cancelled while queued")
    else:
        run.status = RunStatus.CANCEL_REQUESTED.value
        await append_run_event(session, run.id, "run.cancel_requested", "Cancellation requested")

    await session.commit()
    await session.refresh(run)
    return run

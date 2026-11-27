"""Run schedule routes: recurring discovery runs on an interval or a cron expression.

``POST /schedules`` saves the parameters of ``POST /runs`` (query terms, source configs)
with a cadence; the in-process scheduler queues a normal run whenever one is due, applies
the overlap policy (``skip`` / ``buffer_one``) and coalesces missed fires into one run.
``GET /schedules/{id}/history`` is the append-only record of every fire, skip, buffered
fire, coalesced misfire, pause and resume. Schedules only discover and score jobs: no
route applies to a job or contacts an employer.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Annotated, Any, NoReturn

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query, Request, Response, status
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from autoapply_agent.api.deps import get_session
from autoapply_agent.core.time import utc_now
from autoapply_agent.db.models import (
    SQLITE_MAX_INTEGER,
    RunSchedule,
    ScheduleEventKind,
    ScheduleKind,
)
from autoapply_agent.schemas.schedules import (
    CronPreviewRead,
    ScheduleCreate,
    ScheduleDetailRead,
    ScheduleEventRead,
    ScheduleNoteRequest,
    ScheduleRead,
    ScheduleTriggerRead,
    ScheduleUpdate,
    UpcomingFireRead,
)
from autoapply_agent.services.cron import CronError, load_zone
from autoapply_agent.services.job_search import as_utc
from autoapply_agent.services.schedules import (
    DEFAULT_PREVIEW_COUNT,
    MAX_PREVIEW_COUNT,
    ScheduleConflictError,
    ScheduleFilters,
    create_schedule,
    delete_schedule,
    last_run_status,
    list_schedules,
    local_time,
    pause_schedule,
    resume_schedule,
    schedule_events,
    trigger_schedule,
    upcoming_fires,
    update_schedule,
    validate_cron,
)

router = APIRouter(prefix="/schedules", tags=["schedules"])
logger = logging.getLogger(__name__)

ScheduleId = Annotated[int, Path(ge=1, le=SQLITE_MAX_INTEGER)]
_NOT_FOUND: dict[int | str, dict[str, Any]] = {404: {"description": "Schedule not found"}}
_NAME_TAKEN = "schedule with this name already exists"


async def _load(session: AsyncSession, schedule_id: int) -> RunSchedule:
    """Load a schedule or raise a 404."""

    schedule = await session.get(RunSchedule, schedule_id)
    if schedule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="schedule not found")
    return schedule


async def _detail(session: AsyncSession, schedule: RunSchedule) -> ScheduleDetailRead:
    """The detailed view: last run status and the next planned fires."""

    try:
        upcoming = upcoming_fires(schedule, DEFAULT_PREVIEW_COUNT)
    except CronError:
        # A stored time zone this machine's tz database lacks: show the schedule anyway.
        logger.warning("schedule_cadence_unavailable schedule_id=%d", schedule.id)
        upcoming = []
    return ScheduleDetailRead.from_schedule(
        schedule,
        upcoming=upcoming,
        last_run_status=await last_run_status(session, schedule),
    )


async def _commit(session: AsyncSession) -> None:
    """Commit, turning a taken name into a 409."""

    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_NAME_TAKEN) from exc


@router.post(
    "",
    response_model=ScheduleDetailRead,
    status_code=status.HTTP_201_CREATED,
    responses={409: {"description": "A schedule with this name exists"}},
)
async def create_run_schedule(
    request: Request,
    response: Response,
    payload: ScheduleCreate,
    session: AsyncSession = Depends(get_session),
) -> ScheduleDetailRead:
    """Save a recurring discovery run.

    Takes the run parameters of ``POST /runs`` (``query``, ``source_config_ids``) and
    either ``interval_minutes`` (at least 15) or a five-field ``cron`` expression in
    ``timezone``. The first fire is planned right away (``next_run_at``; an interval
    schedule without ``start_at`` fires on the next scheduler tick).

    Args:
        request: Incoming request (``Location`` URL).
        response: Outgoing response.
        payload: Schedule definition.
        session: Request-scoped async session.

    Returns:
        The new schedule with its next planned fires.
    """

    now = utc_now()
    try:
        schedule = await create_schedule(session, payload.to_values(), now=now)
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_NAME_TAKEN) from exc
    await _commit(session)
    logger.info("schedule_created schedule_id=%d kind=%s", schedule.id, schedule.kind)
    response.headers["Location"] = str(request.url_for("get_run_schedule", schedule_id=schedule.id))
    return await _detail(session, schedule)


@router.get("", response_model=list[ScheduleRead])
async def list_run_schedules(
    response: Response,
    paused: bool | None = Query(default=None, description="Only paused / unpaused schedules."),
    kind: ScheduleKind | None = Query(default=None, description="Only interval or cron."),
    q: str | None = Query(
        default=None, max_length=120, description="Case-insensitive name substring."
    ),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0, le=SQLITE_MAX_INTEGER),
    session: AsyncSession = Depends(get_session),
) -> list[ScheduleRead]:
    """List schedules, soonest next fire first (paused ones last).

    The number of matches before ``limit``/``offset`` is in the ``X-Total-Count`` header.

    Args:
        response: Outgoing response (receives ``X-Total-Count``).
        paused: Paused filter.
        kind: Kind filter.
        q: Name filter.
        limit: Page size.
        offset: Matches to skip.
        session: Request-scoped async session.

    Returns:
        One page of schedules.
    """

    total, schedules = await list_schedules(
        session, ScheduleFilters(paused=paused, kind=kind, q=q), limit=limit, offset=offset
    )
    response.headers["X-Total-Count"] = str(total)
    return [ScheduleRead.from_record(schedule) for schedule in schedules]


def _invalid_query(field: str, error_type: str, message: str, value: object) -> NoReturn:
    """Raise a 422 in FastAPI's error shape for one query parameter."""

    raise RequestValidationError(
        [{"type": error_type, "loc": ("query", field), "msg": message, "input": value}]
    )


@router.get("/preview", response_model=CronPreviewRead)
async def preview_cron(
    cron: str = Query(min_length=1, max_length=120, description="Expression to dry-run."),
    timezone: str = Query(default="UTC", max_length=64, description="IANA time zone."),
    count: int = Query(default=DEFAULT_PREVIEW_COUNT, ge=1, le=MAX_PREVIEW_COUNT),
    after: datetime | None = Query(
        default=None, description="List fires after this instant (default: now)."
    ),
) -> CronPreviewRead:
    """Dry-run a cron expression: validate it and list its next fire times.

    Applies the same rules as ``POST /schedules`` (so an expression that fires more often
    than every 15 minutes is a 422) and saves nothing.

    Args:
        cron: Cron expression or macro.
        timezone: IANA time zone of the wall-clock times.
        count: How many fires to list.
        after: Reference instant.

    Returns:
        The normalised expression and its next fires (UTC and local time).
    """

    try:
        expression = validate_cron(cron)
    except CronError as exc:
        _invalid_query("cron", "cron_invalid", f"invalid cron expression: {exc}", cron)
    try:
        zone = load_zone(timezone)
    except CronError as exc:
        _invalid_query("timezone", "timezone_invalid", str(exc), timezone)
    try:
        reference = as_utc(after) if after is not None else utc_now()
    except OverflowError:
        _invalid_query(
            "after", "datetime_utc_range", "Datetime is outside the supported UTC range", None
        )
    fires: list[UpcomingFireRead] = []
    for instant in expression.iter_fires(reference, zone):
        fires.append(UpcomingFireRead(at=instant, local=local_time(instant, zone)))
        if len(fires) >= count:
            break
    return CronPreviewRead(
        cron=expression.source,
        timezone=timezone,
        min_gap_minutes=expression.min_gap_minutes,
        upcoming=fires,
    )


@router.get("/{schedule_id}", response_model=ScheduleDetailRead, responses=_NOT_FOUND)
async def get_run_schedule(
    schedule_id: ScheduleId, session: AsyncSession = Depends(get_session)
) -> ScheduleDetailRead:
    """Get one schedule with its last run status and next five planned fires.

    Args:
        schedule_id: Schedule identifier.
        session: Request-scoped async session.

    Returns:
        The schedule.
    """

    return await _detail(session, await _load(session, schedule_id))


@router.patch(
    "/{schedule_id}",
    response_model=ScheduleDetailRead,
    responses={**_NOT_FOUND, 409: {"description": "A schedule with this name exists"}},
)
async def update_run_schedule(
    schedule_id: ScheduleId,
    payload: ScheduleUpdate,
    session: AsyncSession = Depends(get_session),
) -> ScheduleDetailRead:
    """Change a schedule's name, run parameters, cadence, overlap policy or jitter.

    A cadence change (kind, interval, cron, time zone, start, jitter) re-plans the next
    fire from now. Switching to ``overlap_policy=skip`` drops a buffered fire.

    Args:
        schedule_id: Schedule identifier.
        payload: Fields to change.
        session: Request-scoped async session.

    Returns:
        The updated schedule.
    """

    schedule = await _load(session, schedule_id)
    await update_schedule(session, schedule, payload.to_changes(), now=utc_now())
    await _commit(session)
    return await _detail(session, schedule)


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT, responses=_NOT_FOUND)
async def delete_run_schedule(
    schedule_id: ScheduleId, session: AsyncSession = Depends(get_session)
) -> Response:
    """Delete a schedule and its history; the runs it queued (and their jobs) stay.

    Args:
        schedule_id: Schedule identifier.
        session: Request-scoped async session.

    Returns:
        Empty ``204`` response.
    """

    schedule = await _load(session, schedule_id)
    await delete_schedule(session, schedule)
    await session.commit()
    logger.info("schedule_deleted schedule_id=%d", schedule_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{schedule_id}/pause", response_model=ScheduleDetailRead, responses=_NOT_FOUND)
async def pause_run_schedule(
    schedule_id: ScheduleId,
    payload: ScheduleNoteRequest | None = Body(default=None),
    session: AsyncSession = Depends(get_session),
) -> ScheduleDetailRead:
    """Pause a schedule: it stops firing on its own until resumed (idempotent).

    The optional note is kept as ``pause_note`` and recorded in the history. A buffered
    fire is dropped; manual triggers still work while paused.

    Args:
        schedule_id: Schedule identifier.
        payload: Optional note.
        session: Request-scoped async session.

    Returns:
        The paused schedule.
    """

    schedule = await _load(session, schedule_id)
    note = payload.note if payload is not None else None
    await pause_schedule(session, schedule, note=note, now=utc_now())
    await session.commit()
    return await _detail(session, schedule)


@router.post("/{schedule_id}/resume", response_model=ScheduleDetailRead, responses=_NOT_FOUND)
async def resume_run_schedule(
    schedule_id: ScheduleId,
    payload: ScheduleNoteRequest | None = Body(default=None),
    session: AsyncSession = Depends(get_session),
) -> ScheduleDetailRead:
    """Resume a paused schedule with its next fire after now (idempotent, no catch-up).

    Args:
        schedule_id: Schedule identifier.
        payload: Optional note recorded in the history.
        session: Request-scoped async session.

    Returns:
        The resumed schedule.
    """

    schedule = await _load(session, schedule_id)
    note = payload.note if payload is not None else None
    await resume_schedule(session, schedule, note=note, now=utc_now())
    await session.commit()
    return await _detail(session, schedule)


@router.post(
    "/{schedule_id}/trigger",
    response_model=ScheduleTriggerRead,
    responses={**_NOT_FOUND, 409: {"description": "The schedule changed concurrently; retry"}},
)
async def trigger_run_schedule(
    schedule_id: ScheduleId, session: AsyncSession = Depends(get_session)
) -> ScheduleTriggerRead:
    """Run a schedule now, honouring its overlap policy (also while paused).

    ``outcome`` is ``triggered`` (a run was queued, ``run_id``), ``buffered`` (it starts
    when the active run finishes) or ``skipped_overlap``. The regular cadence is kept.

    Args:
        schedule_id: Schedule identifier.
        session: Request-scoped async session.

    Returns:
        What the trigger did.
    """

    schedule = await _load(session, schedule_id)
    try:
        outcome = await trigger_schedule(session, schedule, now=utc_now())
    except ScheduleConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from None
    logger.info(
        "schedule_%s schedule_id=%d run_id=%s",
        outcome.kind.value,
        schedule.id,
        outcome.run_id or "-",
    )
    return ScheduleTriggerRead(
        outcome=outcome.kind,
        run_id=outcome.run_id,
        reason=outcome.reason,
        schedule=ScheduleRead.from_record(schedule),
    )


@router.get("/{schedule_id}/history", response_model=list[ScheduleEventRead], responses=_NOT_FOUND)
async def get_run_schedule_history(
    schedule_id: ScheduleId,
    response: Response,
    kind: list[ScheduleEventKind] | None = Query(
        default=None, description="Keep these event kinds (repeat for several)."
    ),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0, le=SQLITE_MAX_INTEGER),
    session: AsyncSession = Depends(get_session),
) -> list[ScheduleEventRead]:
    """The schedule's append-only history, newest first.

    Kinds: ``fired``, ``coalesced_misfire``, ``triggered``, ``buffered``,
    ``skipped_overlap``, ``paused``, ``resumed``. The total is in ``X-Total-Count``.

    Args:
        schedule_id: Schedule identifier.
        response: Outgoing response (receives ``X-Total-Count``).
        kind: Kind filter.
        limit: Page size.
        offset: Events to skip.
        session: Request-scoped async session.

    Returns:
        One page of events.
    """

    await _load(session, schedule_id)
    total, events = await schedule_events(
        session, schedule_id, kinds=tuple(dict.fromkeys(kind or ())), limit=limit, offset=offset
    )
    response.headers["X-Total-Count"] = str(total)
    return [ScheduleEventRead.from_record(event) for event in events]

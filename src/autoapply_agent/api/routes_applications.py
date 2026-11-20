"""Application tracker routes: track captured jobs through the application pipeline.

``POST /applications`` starts tracking a job, ``PATCH /applications/{id}`` moves it
through ``saved → applied → interview → offer → accepted / rejected`` (validated by the
state machine in :mod:`~autoapply_agent.services.application_stages`; illegal moves are
``409``), and every change is appended to the application's timeline
(``GET /applications/{id}/events``). Lists, a board view, CSV/JSON Lines exports and an
iCalendar feed of follow-ups read the same data. This is local bookkeeping only: no
route submits an application or contacts an employer.
"""

from __future__ import annotations

import logging
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query, Request, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from autoapply_agent.api.deps import get_session, get_settings
from autoapply_agent.core.config import Settings
from autoapply_agent.core.time import utc_now
from autoapply_agent.db.models import SQLITE_MAX_INTEGER, Application, ApplicationEvent, Job
from autoapply_agent.schemas.applications import (
    ApplicationArchiveRequest,
    ApplicationBoardRead,
    ApplicationCreate,
    ApplicationEventRead,
    ApplicationRead,
    ApplicationUpdate,
    BoardColumnRead,
)
from autoapply_agent.services.application_export import (
    render_applications_csv,
    render_applications_jsonl,
    render_follow_up_calendar,
)
from autoapply_agent.services.application_stages import ApplicationStage, ApplicationStageError
from autoapply_agent.services.application_tracker import (
    DUE_SOON_DAYS,
    MAX_DUE_WITHIN_DAYS,
    AlreadyTrackedError,
    ApplicationFilters,
    ApplicationSort,
    FollowUpFilter,
    JobNotFoundError,
    application_events,
    board,
    get_tracked,
    latest_sequences,
    list_applications,
    set_archived,
    track_job,
    update_application,
)

router = APIRouter(prefix="/applications", tags=["applications"])
logger = logging.getLogger(__name__)

ApplicationId = Annotated[int, Path(ge=1, le=SQLITE_MAX_INTEGER)]
EXPORT_MEDIA_TYPES: dict[str, str] = {
    "csv": "text/csv; charset=utf-8",
    "jsonl": "application/x-ndjson",
}
ICS_MEDIA_TYPE = "text/calendar; charset=utf-8"
_NOT_FOUND: dict[int | str, dict[str, Any]] = {404: {"description": "Application not found"}}
_CONCURRENT_UPDATE = "application was changed by another request; retry"


def get_application_filters(
    stage: list[ApplicationStage] | None = Query(
        default=None, description="Keep these stages (repeat the parameter for several)."
    ),
    company: str | None = Query(
        default=None, max_length=256, description="Case-insensitive company substring."
    ),
    q: str | None = Query(
        default=None,
        max_length=200,
        description="Space-separated terms; each must match the job title, company or "
        "location, or the application's notes or next action.",
    ),
    follow_up: FollowUpFilter | None = Query(
        default=None,
        description="overdue: follow-up time passed; due: before now + due_within_days "
        "(overdue included); scheduled: any follow-up; none: no follow-up.",
    ),
    due_within_days: int = Query(
        default=DUE_SOON_DAYS,
        ge=0,
        le=MAX_DUE_WITHIN_DAYS,
        description="Horizon of follow_up=due, in days.",
    ),
    include_archived: bool = Query(default=False, description="Include archived applications."),
    job_id: int | None = Query(
        default=None, ge=1, le=SQLITE_MAX_INTEGER, description="Only the application of this job."
    ),
    sort: ApplicationSort = Query(
        default=ApplicationSort.UPDATED,
        description="updated / created (newest first), next_action (soonest first), applied "
        "(latest first), score (job score, highest first); missing dates sort last.",
    ),
) -> ApplicationFilters:
    """Parse the filter query parameters shared by list, board, export and calendar."""

    return ApplicationFilters(
        stages=tuple(dict.fromkeys(stage or ())),
        company=company,
        q=q,
        follow_up=follow_up,
        due_within_days=due_within_days,
        include_archived=include_archived,
        job_id=job_id,
        sort=sort,
    )


async def _load(session: AsyncSession, application_id: int) -> tuple[Application, Job]:
    """Load an application and its job, or raise a 404."""

    tracked = await get_tracked(session, application_id)
    if tracked is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="application not found")
    return tracked


async def _commit(session: AsyncSession) -> None:
    """Commit, turning a lost race on the timeline sequence into a 409."""

    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=_CONCURRENT_UPDATE
        ) from exc


@router.post(
    "",
    response_model=ApplicationRead,
    status_code=status.HTTP_201_CREATED,
    responses={
        404: {"description": "Job not found"},
        409: {"description": "The job (or another capture of its posting URL) is tracked"},
    },
)
async def create_application(
    request: Request,
    response: Response,
    payload: ApplicationCreate,
    session: AsyncSession = Depends(get_session),
) -> ApplicationRead:
    """Start tracking a captured job.

    One application per job: tracking it again, or tracking another capture of the same
    posting URL, is a ``409`` whose ``Location`` header points at the existing
    application.

    Args:
        request: Incoming request (``Location`` URLs).
        response: Outgoing response (``Location`` of the new application).
        payload: Job and optional starting stage, notes and follow-up.
        session: Request-scoped async session.

    Returns:
        The new application.
    """

    now = utc_now()
    try:
        application, job = await track_job(
            session,
            payload.job_id,
            now=now,
            stage=payload.stage,
            notes=payload.notes,
            note=payload.note,
            applied_at=payload.applied_at,
            next_action_at=payload.next_action_at,
            next_action=payload.next_action,
        )
    except JobNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job not found") from None
    except AlreadyTrackedError as exc:
        location = str(request.url_for("get_application", application_id=exc.application_id))
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc), headers={"Location": location}
        ) from None
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"job {payload.job_id} is already tracked",
        ) from exc
    logger.info(
        "application_tracked application_id=%d job_id=%d stage=%s",
        application.id,
        job.id,
        application.stage,
    )
    response.headers["Location"] = str(
        request.url_for("get_application", application_id=application.id)
    )
    return ApplicationRead.from_records(application, job, now=now)


@router.get("", response_model=list[ApplicationRead])
async def list_tracked_applications(
    response: Response,
    filters: ApplicationFilters = Depends(get_application_filters),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0, le=SQLITE_MAX_INTEGER),
    session: AsyncSession = Depends(get_session),
) -> list[ApplicationRead]:
    """List tracked applications with filters, sorting and paging.

    Archived applications are hidden unless ``include_archived=true``. The number of
    matches before ``limit``/``offset`` is returned in the ``X-Total-Count`` header.

    Args:
        response: Outgoing response (receives ``X-Total-Count``).
        filters: Parsed filters and sort.
        limit: Max applications to return.
        offset: Number of matches to skip.
        session: Request-scoped async session.

    Returns:
        One page of applications.
    """

    now = utc_now()
    page = await list_applications(session, filters, now=now, limit=limit, offset=offset)
    response.headers["X-Total-Count"] = str(page.total)
    return [ApplicationRead.from_records(app, job, now=now) for app, job in page.items]


@router.get("/board", response_model=ApplicationBoardRead)
async def application_board(
    filters: ApplicationFilters = Depends(get_application_filters),
    per_stage: int = Query(default=20, ge=1, le=100, description="Cards per stage column."),
    session: AsyncSession = Depends(get_session),
) -> ApplicationBoardRead:
    """Group applications by stage, one column per stage in pipeline order.

    Every stage gets a column (``saved``, ``applied``, ``interview``, ``offer``,
    ``accepted``, ``rejected``) with its count and first ``per_stage`` cards in the
    requested sort; ``stage`` limits which columns are filled. ``follow_ups`` counts
    the matching applications per follow-up status.

    Args:
        filters: Parsed filters and sort.
        per_stage: Cards per column.
        session: Request-scoped async session.

    Returns:
        The board.
    """

    now = utc_now()
    result = await board(session, filters, now=now, per_stage=per_stage)
    return ApplicationBoardRead(
        total=result.total,
        include_archived=filters.include_archived,
        follow_ups=result.follow_ups,
        columns=[
            BoardColumnRead(
                stage=column.stage,
                count=column.count,
                applications=[
                    ApplicationRead.from_records(app, job, now=now) for app, job in column.items
                ],
            )
            for column in result.columns
        ],
    )


@router.get(
    "/export",
    response_class=Response,
    responses={
        200: {
            "description": "CSV (OWASP CSV-injection safe) or JSON Lines attachment.",
            "content": {"text/csv": {}, "application/x-ndjson": {}},
        }
    },
)
async def export_applications(
    filters: ApplicationFilters = Depends(get_application_filters),
    export_format: Literal["csv", "jsonl"] = Query(
        default="csv", alias="format", description="csv (spreadsheets) or jsonl."
    ),
    limit: int | None = Query(
        default=None, ge=1, le=100_000, description="Optional cap; every match by default."
    ),
    session: AsyncSession = Depends(get_session),
) -> Response:
    """Download the matching applications as CSV or JSON Lines.

    Args:
        filters: Parsed filters and sort.
        export_format: ``csv`` or ``jsonl``.
        limit: Optional maximum number of rows.
        session: Request-scoped async session.

    Returns:
        Attachment response.
    """

    now = utc_now()
    page = await list_applications(session, filters, now=now, limit=limit)
    body = (
        render_applications_csv(page.items, now=now)
        if export_format == "csv"
        else render_applications_jsonl(page.items, now=now)
    )
    filename = f"applications-{now:%Y%m%dT%H%M%SZ}.{export_format}"
    return Response(
        content=body,
        media_type=EXPORT_MEDIA_TYPES[export_format],
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Total-Count": str(page.total),
        },
    )


@router.get(
    "/calendar.ics",
    response_class=Response,
    responses={200: {"description": "iCalendar (RFC 5545).", "content": {"text/calendar": {}}}},
)
async def follow_up_calendar(
    request: Request,
    filters: ApplicationFilters = Depends(get_application_filters),
    limit: int = Query(default=1000, ge=1, le=10_000, description="Maximum events."),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> Response:
    """Publish follow-ups as an iCalendar feed (one event per scheduled follow-up).

    Subscribe to it from a calendar app. Events are 30 minutes, marked free, titled
    with the follow-up label and the role; their description holds the stage, applied
    date and links, never the notes. Takes the list filters (``follow_up`` narrows
    within scheduled follow-ups); events come soonest first.

    Args:
        request: Incoming request (application links and event UIDs).
        filters: Parsed filters.
        limit: Maximum number of events.
        session: Request-scoped async session.
        settings: Application settings (calendar name).

    Returns:
        ``text/calendar`` response.
    """

    now = utc_now()
    scheduled = ApplicationFilters(
        stages=filters.stages,
        company=filters.company,
        q=filters.q,
        follow_up=filters.follow_up or FollowUpFilter.SCHEDULED,
        due_within_days=filters.due_within_days,
        include_archived=filters.include_archived,
        job_id=filters.job_id,
        sort=ApplicationSort.NEXT_ACTION,
    )
    page = await list_applications(session, scheduled, now=now, limit=limit)
    revisions = await latest_sequences(session, [app.id for app, _ in page.items])

    def application_url(application: Application) -> str:
        return str(request.url_for("get_application", application_id=application.id))

    document = render_follow_up_calendar(
        page.items,
        calendar_name=f"{settings.app_name} follow-ups",
        generated_at=now,
        application_url=application_url,
        revisions=revisions,
    )
    return Response(
        content=document,
        media_type=ICS_MEDIA_TYPE,
        headers={"Content-Disposition": 'inline; filename="follow-ups.ics"'},
    )


@router.get("/{application_id}", response_model=ApplicationRead, responses=_NOT_FOUND)
async def get_application(
    application_id: ApplicationId,
    session: AsyncSession = Depends(get_session),
) -> ApplicationRead:
    """Get one application with its follow-up state and a summary of its job.

    Args:
        application_id: Application identifier.
        session: Request-scoped async session.

    Returns:
        The application.
    """

    application, job = await _load(session, application_id)
    return ApplicationRead.from_records(application, job, now=utc_now())


@router.patch(
    "/{application_id}",
    response_model=ApplicationRead,
    responses={
        **_NOT_FOUND,
        409: {"description": "Illegal stage move, or a concurrent update"},
    },
)
async def update_tracked_application(
    application_id: ApplicationId,
    payload: ApplicationUpdate,
    session: AsyncSession = Depends(get_session),
) -> ApplicationRead:
    """Move an application to another stage, reschedule its follow-up or annotate it.

    Stage moves must follow the state machine (``saved → applied | rejected``,
    ``applied → interview | rejected``, ``interview → offer | rejected``,
    ``offer → accepted | rejected``); anything else is a ``409`` and changes nothing.
    Each request appends at most one timeline event.

    Args:
        application_id: Application identifier.
        payload: Fields to change.
        session: Request-scoped async session.

    Returns:
        The updated application.
    """

    application, job = await _load(session, application_id)
    now = utc_now()
    try:
        event = await update_application(session, application, payload.to_patch(), now=now)
    except ApplicationStageError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from None
    await _commit(session)
    if event is not None:
        logger.info(
            "application_updated application_id=%d event=%s sequence=%d",
            application.id,
            event.event_type,
            event.sequence,
        )
    return ApplicationRead.from_records(application, job, now=now)


@router.get(
    "/{application_id}/events", response_model=list[ApplicationEventRead], responses=_NOT_FOUND
)
async def get_application_events(
    application_id: ApplicationId,
    session: AsyncSession = Depends(get_session),
) -> list[ApplicationEventRead]:
    """Return the application's append-only timeline, oldest first.

    Args:
        application_id: Application identifier.
        session: Request-scoped async session.

    Returns:
        Ordered events.
    """

    await _load(session, application_id)
    events: list[ApplicationEvent] = await application_events(session, application_id)
    return [ApplicationEventRead.from_record(event) for event in events]


async def _set_archived(
    session: AsyncSession,
    application_id: int,
    archived: bool,
    payload: ApplicationArchiveRequest | None,
) -> ApplicationRead:
    """Archive or unarchive, then return the fresh view."""

    application, job = await _load(session, application_id)
    now = utc_now()
    event = await set_archived(
        session,
        application,
        archived,
        now=now,
        note=payload.note if payload is not None else None,
    )
    await _commit(session)
    if event is not None:
        logger.info(
            "application_updated application_id=%d event=%s sequence=%d",
            application.id,
            event.event_type,
            event.sequence,
        )
    return ApplicationRead.from_records(application, job, now=now)


@router.post("/{application_id}/archive", response_model=ApplicationRead, responses=_NOT_FOUND)
async def archive_application(
    application_id: ApplicationId,
    payload: ApplicationArchiveRequest | None = Body(default=None),
    session: AsyncSession = Depends(get_session),
) -> ApplicationRead:
    """Archive an application: hidden by default, stage and timeline kept (idempotent).

    Args:
        application_id: Application identifier.
        payload: Optional timeline note.
        session: Request-scoped async session.

    Returns:
        The archived application.
    """

    return await _set_archived(session, application_id, True, payload)


@router.post("/{application_id}/unarchive", response_model=ApplicationRead, responses=_NOT_FOUND)
async def unarchive_application(
    application_id: ApplicationId,
    payload: ApplicationArchiveRequest | None = Body(default=None),
    session: AsyncSession = Depends(get_session),
) -> ApplicationRead:
    """Bring an archived application back (idempotent).

    Args:
        application_id: Application identifier.
        payload: Optional timeline note.
        session: Request-scoped async session.

    Returns:
        The unarchived application.
    """

    return await _set_archived(session, application_id, False, payload)

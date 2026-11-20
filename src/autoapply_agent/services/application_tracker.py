"""Persistent job-application tracker: pipeline stages, follow-ups and an audit trail.

Tracks captured jobs (:class:`~autoapply_agent.db.models.Job`) through
``saved → applied → interview → offer → accepted / rejected`` in the ``applications``
table. Every stage move is validated by the single state machine in
:mod:`~autoapply_agent.services.application_stages` and every change is appended to
``application_events`` (stage moves, follow-up and applied-date changes, timeline notes,
archiving), so the history of an application can be audited and is never rewritten.

The HTTP routes (``/applications``) write through this module; the read-only MCP tools
only use its queries. Nothing here submits an application, contacts an employer or
touches the network: it is local pipeline bookkeeping.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, StrEnum
from typing import Any, Final

from sqlalchemy import ColumnElement, Select, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from autoapply_agent.db.models import Application, ApplicationEvent, Job
from autoapply_agent.services.application_stages import (
    PIPELINE_ORDER,
    ApplicationStage,
    check_transition,
)
from autoapply_agent.services.job_export import rfc3339
from autoapply_agent.services.job_search import as_utc

MAX_NOTES_CHARS = 10_000
"""Longest accepted ``notes`` text (the application's editable scratchpad)."""
MAX_EVENT_NOTE_CHARS = 2_000
"""Longest accepted timeline ``note`` (stored with one event, never edited)."""
MAX_NEXT_ACTION_CHARS = 200
"""Longest accepted ``next_action`` label (what to do at ``next_action_at``)."""
DUE_SOON_DAYS = 7
"""Follow-ups due within this many days are ``due`` (Teal and Huntr nudge after a week)."""
MAX_DUE_WITHIN_DAYS = 366


class ApplicationEventType(StrEnum):
    """Kinds of entries in an application's timeline."""

    TRACKED = "tracked"
    STAGE_CHANGED = "stage_changed"
    UPDATED = "updated"
    NOTE_ADDED = "note_added"
    ARCHIVED = "archived"
    UNARCHIVED = "unarchived"


class FollowUpStatus(StrEnum):
    """Where an application's follow-up (``next_action_at``) stands right now."""

    OVERDUE = "overdue"
    DUE = "due"
    SCHEDULED = "scheduled"
    NONE = "none"


class FollowUpFilter(StrEnum):
    """``follow_up`` list filter values.

    ``overdue``: the follow-up time has passed; ``due``: it falls before now plus
    ``due_within_days`` (overdue included); ``scheduled``: any follow-up is set;
    ``none``: no follow-up is set.
    """

    OVERDUE = "overdue"
    DUE = "due"
    SCHEDULED = "scheduled"
    NONE = "none"


class ApplicationSort(StrEnum):
    """Supported orderings; ``id`` breaks ties so paging is stable."""

    UPDATED = "updated"
    CREATED = "created"
    NEXT_ACTION = "next_action"
    APPLIED = "applied"
    SCORE = "score"


class _Unset(Enum):
    """Marker type for "field not provided" in :class:`ApplicationPatch`."""

    UNSET = "unset"


UNSET: Final = _Unset.UNSET


class JobNotFoundError(LookupError):
    """The job to track does not exist."""


class AlreadyTrackedError(Exception):
    """The job, or another capture of the same posting URL, is already tracked.

    Attributes:
        application_id: The existing application.
        job_id: The job that application tracks.
        same_posting: True when it tracks another capture of the same posting URL.
    """

    def __init__(self, application_id: int, job_id: int, *, same_posting: bool) -> None:
        self.application_id = application_id
        self.job_id = job_id
        self.same_posting = same_posting
        if same_posting:
            message = (
                f"this posting is already tracked as application {application_id} "
                f"(job {job_id} has the same URL)"
            )
        else:
            message = f"job {job_id} is already tracked as application {application_id}"
        super().__init__(message)


@dataclass(slots=True, frozen=True)
class ApplicationFilters:
    """Filters shared by the list, board, export and calendar endpoints.

    Attributes:
        stages: Keep these stages only (empty keeps every stage).
        company: Case-insensitive substring of the job's company.
        q: Whitespace-separated terms; each must match the job's title, company or
            location, or the application's notes or next action.
        follow_up: Follow-up filter (see :class:`FollowUpFilter`).
        due_within_days: Horizon of ``follow_up=due``.
        include_archived: Whether archived applications are included.
        job_id: Only the application tracking this job.
        sort: Result ordering.
    """

    stages: tuple[ApplicationStage, ...] = ()
    company: str | None = None
    q: str | None = None
    follow_up: FollowUpFilter | None = None
    due_within_days: int = DUE_SOON_DAYS
    include_archived: bool = False
    job_id: int | None = None
    sort: ApplicationSort = ApplicationSort.UPDATED


@dataclass(slots=True, frozen=True)
class ApplicationPatch:
    """One update request; fields left :data:`UNSET` are not changed.

    Attributes:
        stage: Target stage (``None`` keeps the current one).
        note: Timeline note recorded with this update's event.
        notes: New scratchpad text (``None`` clears it).
        applied_at: When the application was sent (``None`` clears it).
        next_action_at: Follow-up time (``None`` clears it, and the label unless one is
            given in the same patch).
        next_action: Follow-up label (``None`` clears it).
    """

    stage: ApplicationStage | None = None
    note: str | None = None
    notes: str | None | _Unset = UNSET
    applied_at: datetime | None | _Unset = UNSET
    next_action_at: datetime | None | _Unset = UNSET
    next_action: str | None | _Unset = UNSET


@dataclass(slots=True, frozen=True)
class ApplicationPage:
    """One page of tracked applications with the total number of matches."""

    total: int
    items: list[tuple[Application, Job]]


@dataclass(slots=True, frozen=True)
class BoardColumn:
    """One stage column of the board."""

    stage: ApplicationStage
    count: int
    items: list[tuple[Application, Job]]


@dataclass(slots=True, frozen=True)
class Board:
    """Applications grouped by stage, in pipeline order, plus follow-up counts."""

    total: int
    columns: list[BoardColumn]
    follow_ups: dict[str, int] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Derived values
# ---------------------------------------------------------------------------


def follow_up_status(next_action_at: datetime | None, now: datetime) -> FollowUpStatus:
    """Classify a follow-up time against ``now``.

    Args:
        next_action_at: Follow-up time (naive values are UTC), possibly missing.
        now: Current time.

    Returns:
        ``overdue`` before ``now``, ``due`` within :data:`DUE_SOON_DAYS` days,
        ``scheduled`` later, ``none`` when unset.
    """

    if next_action_at is None:
        return FollowUpStatus.NONE
    moment = as_utc(next_action_at)
    if moment < now:
        return FollowUpStatus.OVERDUE
    if moment <= now + timedelta(days=DUE_SOON_DAYS):
        return FollowUpStatus.DUE
    return FollowUpStatus.SCHEDULED


def days_in_stage(application: Application, now: datetime) -> int:
    """Whole days since the application entered its current stage (never negative)."""

    return max(0, (now - as_utc(application.stage_changed_at)).days)


def _utc(value: datetime | None) -> datetime | None:
    """Normalize an optional timestamp to aware UTC before it is stored.

    SQLite keeps only the wall-clock digits of a datetime, so every stored value must
    already be UTC for comparisons and the follow-up filters to be correct.
    """

    return as_utc(value) if value is not None else None


def _instant(value: datetime | None) -> str | None:
    """RFC 3339 rendering of an optional timestamp for event ``changes``."""

    return rfc3339(value) if value is not None else None


def _same_instant(left: datetime | None, right: datetime | None) -> bool:
    """Compare optional timestamps, treating naive values (SQLite) as UTC."""

    if left is None or right is None:
        return left is right
    return as_utc(left) == as_utc(right)


# ---------------------------------------------------------------------------
# Writes
# ---------------------------------------------------------------------------


async def _append_event(
    session: AsyncSession,
    application: Application,
    event_type: ApplicationEventType,
    *,
    now: datetime,
    from_stage: ApplicationStage | None = None,
    to_stage: ApplicationStage | None = None,
    note: str | None = None,
    changes: dict[str, Any] | None = None,
) -> ApplicationEvent:
    """Append the next event of ``application`` (sequence numbers start at 1).

    Two concurrent writers compute the same sequence; the unique
    ``(application_id, sequence)`` constraint then rejects the second one, so a
    timeline can never interleave two racing stage moves.
    """

    current = await session.scalar(
        select(func.coalesce(func.max(ApplicationEvent.sequence), 0)).where(
            ApplicationEvent.application_id == application.id
        )
    )
    event = ApplicationEvent(
        application_id=application.id,
        sequence=int(current or 0) + 1,
        event_type=event_type.value,
        from_stage=from_stage.value if from_stage is not None else None,
        to_stage=to_stage.value if to_stage is not None else None,
        note=note,
        changes=changes or None,
        created_at=now,
    )
    session.add(event)
    await session.flush()
    return event


async def track_job(
    session: AsyncSession,
    job_id: int,
    *,
    now: datetime,
    stage: ApplicationStage = ApplicationStage.SAVED,
    notes: str | None = None,
    note: str | None = None,
    applied_at: datetime | None = None,
    next_action_at: datetime | None = None,
    next_action: str | None = None,
) -> tuple[Application, Job]:
    """Start tracking a captured job (the caller commits).

    Any stage may be the starting stage (a job applied to elsewhere can start at
    ``applied``); later moves follow the state machine. Starting at ``applied``
    without ``applied_at`` records ``now`` as the applied time.

    Args:
        session: Active async DB session.
        job_id: Captured job to track.
        now: Current time (recorded on the application and its first event).
        stage: Starting stage.
        notes: Scratchpad text.
        note: Note for the ``tracked`` timeline event.
        applied_at: When the application was sent.
        next_action_at: Follow-up time.
        next_action: Follow-up label.

    Returns:
        The new application and its job.

    Raises:
        JobNotFoundError: If ``job_id`` does not exist.
        AlreadyTrackedError: If the job, or another capture of its posting URL, is tracked.
    """

    job = await session.get(Job, job_id)
    if job is None:
        raise JobNotFoundError(job_id)
    existing = await session.scalar(select(Application).where(Application.job_id == job_id))
    if existing is not None:
        raise AlreadyTrackedError(existing.id, job_id, same_posting=False)
    # A later run re-captures a posting as a new job row; the posting URL (compared the
    # way GET /jobs?dedupe=true compares it) keeps it from being tracked twice.
    same_posting = (
        await session.execute(
            select(Application.id, Job.id)
            .join(Job, Job.id == Application.job_id)
            .where(func.lower(func.trim(Job.url)) == func.lower(func.trim(job.url)))
            .order_by(Application.id.asc())
            .limit(1)
        )
    ).first()
    if same_posting is not None:
        raise AlreadyTrackedError(same_posting[0], same_posting[1], same_posting=True)

    applied_at, next_action_at = _utc(applied_at), _utc(next_action_at)
    if stage is ApplicationStage.APPLIED and applied_at is None:
        applied_at = now
    application = Application(
        job_id=job_id,
        stage=stage.value,
        archived=False,
        notes=notes,
        applied_at=applied_at,
        next_action_at=next_action_at,
        next_action=next_action,
        stage_changed_at=now,
        created_at=now,
        updated_at=now,
    )
    session.add(application)
    await session.flush()
    initial = {
        "job_id": job_id,
        "applied_at": _instant(applied_at),
        "next_action_at": _instant(next_action_at),
        "next_action": next_action,
    }
    await _append_event(
        session,
        application,
        ApplicationEventType.TRACKED,
        now=now,
        to_stage=stage,
        note=note,
        changes={key: value for key, value in initial.items() if value is not None},
    )
    return application, job


def _change(changes: dict[str, Any], name: str, before: Any, after: Any) -> None:
    """Record ``name: {from, to}`` in an event's ``changes``."""

    changes[name] = {"from": before, "to": after}


async def update_application(
    session: AsyncSession,
    application: Application,
    patch: ApplicationPatch,
    *,
    now: datetime,
) -> ApplicationEvent | None:
    """Apply ``patch`` and append one timeline event describing it (the caller commits).

    The stage move is validated before anything changes, so an illegal move leaves
    the application untouched. Moving to the current stage is not a move. The event
    is ``stage_changed`` when the stage moves, ``updated`` when only the follow-up or
    applied time change, ``note_added`` when only a timeline note is given; editing
    ``notes`` (the scratchpad) alone records no event.

    Args:
        session: Active async DB session.
        application: Application to update.
        patch: Requested changes.
        now: Current time.

    Returns:
        The appended event, or None when nothing was recorded.

    Raises:
        ApplicationStageError: If the stage move is not allowed.
    """

    current = ApplicationStage(application.stage)
    target = patch.stage if patch.stage is not None and patch.stage != current else None
    if target is not None:
        check_transition(current, target)

    changes: dict[str, Any] = {}
    touched = False
    if target is not None:
        application.stage = target.value
        application.stage_changed_at = now
        touched = True
        if (
            target is ApplicationStage.APPLIED
            and application.applied_at is None
            and patch.applied_at is UNSET
        ):
            _change(changes, "applied_at", None, _instant(now))
            application.applied_at = now
    if patch.applied_at is not UNSET:
        applied_at = _utc(patch.applied_at)
        if not _same_instant(applied_at, application.applied_at):
            _change(changes, "applied_at", _instant(application.applied_at), _instant(applied_at))
            application.applied_at = applied_at
    next_action = patch.next_action
    if patch.next_action_at is not UNSET:
        next_action_at = _utc(patch.next_action_at)
        if next_action_at is None and next_action is UNSET:
            next_action = None
        if not _same_instant(next_action_at, application.next_action_at):
            _change(
                changes,
                "next_action_at",
                _instant(application.next_action_at),
                _instant(next_action_at),
            )
            application.next_action_at = next_action_at
    if next_action is not UNSET and next_action != application.next_action:
        _change(changes, "next_action", application.next_action, next_action)
        application.next_action = next_action
    if patch.notes is not UNSET and patch.notes != application.notes:
        application.notes = patch.notes
        touched = True

    event: ApplicationEvent | None = None
    if target is not None:
        event = await _append_event(
            session,
            application,
            ApplicationEventType.STAGE_CHANGED,
            now=now,
            from_stage=current,
            to_stage=target,
            note=patch.note,
            changes=changes,
        )
    elif changes:
        event = await _append_event(
            session,
            application,
            ApplicationEventType.UPDATED,
            now=now,
            note=patch.note,
            changes=changes,
        )
    elif patch.note is not None:
        event = await _append_event(
            session, application, ApplicationEventType.NOTE_ADDED, now=now, note=patch.note
        )
    if touched or event is not None:
        application.updated_at = now
    return event


async def set_archived(
    session: AsyncSession,
    application: Application,
    archived: bool,
    *,
    now: datetime,
    note: str | None = None,
) -> ApplicationEvent | None:
    """Archive or unarchive an application (the caller commits).

    Archiving hides an application from lists, the board, exports and the calendar
    unless ``include_archived`` is set; its stage and history are kept. Repeating
    the current state is a no-op (a note given with it is still recorded).

    Args:
        session: Active async DB session.
        application: Application to change.
        archived: Desired state.
        now: Current time.
        note: Optional timeline note.

    Returns:
        The appended event, or None when nothing was recorded.
    """

    if application.archived == archived:
        if note is None:
            return None
        event = await _append_event(
            session, application, ApplicationEventType.NOTE_ADDED, now=now, note=note
        )
    else:
        application.archived = archived
        event = await _append_event(
            session,
            application,
            ApplicationEventType.ARCHIVED if archived else ApplicationEventType.UNARCHIVED,
            now=now,
            note=note,
            changes={"archived": {"from": not archived, "to": archived}},
        )
    application.updated_at = now
    return event


# ---------------------------------------------------------------------------
# Reads (shared with the read-only MCP tools)
# ---------------------------------------------------------------------------


def build_conditions(
    filters: ApplicationFilters, *, now: datetime, include_stages: bool = True
) -> list[ColumnElement[bool]]:
    """Translate filters into SQL conditions over ``applications`` joined to ``jobs``.

    Args:
        filters: Requested filters.
        now: Reference time of the follow-up filters.
        include_stages: Whether to apply ``filters.stages`` (the board groups by stage).

    Returns:
        Conditions to combine with AND.
    """

    conditions: list[ColumnElement[bool]] = []
    if include_stages and filters.stages:
        conditions.append(Application.stage.in_([stage.value for stage in filters.stages]))
    if not filters.include_archived:
        conditions.append(Application.archived.is_(False))
    if filters.job_id is not None:
        conditions.append(Application.job_id == filters.job_id)
    if filters.company and filters.company.strip():
        conditions.append(Job.company.icontains(filters.company.strip(), autoescape=True))
    for term in (filters.q or "").split():
        conditions.append(
            or_(
                Job.title.icontains(term, autoescape=True),
                Job.company.icontains(term, autoescape=True),
                Job.location.icontains(term, autoescape=True),
                Application.notes.icontains(term, autoescape=True),
                Application.next_action.icontains(term, autoescape=True),
            )
        )
    moment = as_utc(now)
    if filters.follow_up is FollowUpFilter.OVERDUE:
        conditions.append(Application.next_action_at < moment)
    elif filters.follow_up is FollowUpFilter.DUE:
        horizon = moment + timedelta(days=filters.due_within_days)
        conditions.append(Application.next_action_at <= horizon)
    elif filters.follow_up is FollowUpFilter.SCHEDULED:
        conditions.append(Application.next_action_at.is_not(None))
    elif filters.follow_up is FollowUpFilter.NONE:
        conditions.append(Application.next_action_at.is_(None))
    return conditions


def _order_by(sort: ApplicationSort) -> tuple[ColumnElement[Any], ...]:
    """``ORDER BY`` clauses; nulls sort last, ``id`` breaks ties."""

    if sort is ApplicationSort.CREATED:
        return (Application.created_at.desc(), Application.id.desc())
    if sort is ApplicationSort.NEXT_ACTION:
        return (
            Application.next_action_at.is_(None).asc(),
            Application.next_action_at.asc(),
            Application.id.asc(),
        )
    if sort is ApplicationSort.APPLIED:
        return (
            Application.applied_at.is_(None).asc(),
            Application.applied_at.desc(),
            Application.id.desc(),
        )
    if sort is ApplicationSort.SCORE:
        return (Job.score.desc(), Application.updated_at.desc(), Application.id.desc())
    return (Application.updated_at.desc(), Application.id.desc())


def _select(conditions: Sequence[ColumnElement[bool]]) -> Select[tuple[Application, Job]]:
    """``SELECT applications, jobs`` joined on the tracked job."""

    return select(Application, Job).join(Job, Job.id == Application.job_id).where(*conditions)


async def get_tracked(session: AsyncSession, application_id: int) -> tuple[Application, Job] | None:
    """Load one application with its job, or None."""

    row = (await session.execute(_select([Application.id == application_id]))).first()
    return None if row is None else (row[0], row[1])


async def list_applications(
    session: AsyncSession,
    filters: ApplicationFilters,
    *,
    now: datetime,
    limit: int | None,
    offset: int = 0,
) -> ApplicationPage:
    """Return one page of matching applications and the total number of matches.

    Args:
        session: Active async DB session.
        filters: Requested filters and sort.
        now: Reference time of the follow-up filters.
        limit: Maximum number of applications (None: all).
        offset: Number of matches to skip.

    Returns:
        Page of ``(application, job)`` pairs.
    """

    conditions = build_conditions(filters, now=now)
    total = await session.scalar(
        select(func.count())
        .select_from(Application)
        .join(Job, Job.id == Application.job_id)
        .where(*conditions)
    )
    statement = _select(conditions).order_by(*_order_by(filters.sort)).offset(offset)
    if limit is not None:
        statement = statement.limit(limit)
    rows = (await session.execute(statement)).tuples().all()
    return ApplicationPage(total=int(total or 0), items=[(row[0], row[1]) for row in rows])


async def follow_up_counts(
    session: AsyncSession, filters: ApplicationFilters, *, now: datetime
) -> dict[str, int]:
    """Count the matching applications per :class:`FollowUpStatus`."""

    moment = as_utc(now)
    status = case(
        (Application.next_action_at.is_(None), FollowUpStatus.NONE.value),
        (Application.next_action_at < moment, FollowUpStatus.OVERDUE.value),
        (
            Application.next_action_at <= moment + timedelta(days=DUE_SOON_DAYS),
            FollowUpStatus.DUE.value,
        ),
        else_=FollowUpStatus.SCHEDULED.value,
    )
    rows = await session.execute(
        select(status, func.count())
        .select_from(Application)
        .join(Job, Job.id == Application.job_id)
        .where(*build_conditions(filters, now=now))
        .group_by(status)
    )
    counts = {item.value: 0 for item in FollowUpStatus}
    counts.update({str(name): int(count) for name, count in rows.tuples()})
    return counts


async def stage_counts(
    session: AsyncSession, filters: ApplicationFilters, *, now: datetime
) -> dict[str, int]:
    """Count the applications matching every filter but ``stages``, per stage."""

    rows = await session.execute(
        select(Application.stage, func.count())
        .select_from(Application)
        .join(Job, Job.id == Application.job_id)
        .where(*build_conditions(filters, now=now, include_stages=False))
        .group_by(Application.stage)
    )
    counts = {stage.value: 0 for stage in PIPELINE_ORDER}
    counts.update({str(stage): int(count) for stage, count in rows.tuples()})
    return counts


async def board(
    session: AsyncSession,
    filters: ApplicationFilters,
    *,
    now: datetime,
    per_stage: int,
) -> Board:
    """Group matching applications by stage, one column per stage in pipeline order.

    Args:
        session: Active async DB session.
        filters: Filters (``stages`` limits which columns get cards) and sort.
        now: Reference time of the follow-up filters.
        per_stage: Maximum number of cards per column.

    Returns:
        Board with every stage column, its count and its first ``per_stage`` cards.
    """

    counts = await stage_counts(session, filters, now=now)
    wanted = set(filters.stages) or set(PIPELINE_ORDER)
    columns: list[BoardColumn] = []
    for stage in PIPELINE_ORDER:
        count = counts.get(stage.value, 0) if stage in wanted else 0
        items: list[tuple[Application, Job]] = []
        if count:
            conditions = [
                *build_conditions(filters, now=now, include_stages=False),
                Application.stage == stage.value,
            ]
            rows = await session.execute(
                _select(conditions).order_by(*_order_by(filters.sort)).limit(per_stage)
            )
            items = [(row[0], row[1]) for row in rows.tuples()]
        columns.append(BoardColumn(stage=stage, count=count, items=items))
    return Board(
        total=sum(column.count for column in columns),
        columns=columns,
        follow_ups=await follow_up_counts(session, filters, now=now),
    )


async def application_events(
    session: AsyncSession, application_id: int, *, limit: int | None = None
) -> list[ApplicationEvent]:
    """Return an application's timeline in sequence order.

    Args:
        session: Active async DB session.
        application_id: Application identifier.
        limit: Optional maximum; keeps the most recent events.

    Returns:
        Events ordered by ascending ``sequence``.
    """

    statement = select(ApplicationEvent).where(ApplicationEvent.application_id == application_id)
    if limit is None:
        return list(await session.scalars(statement.order_by(ApplicationEvent.sequence.asc())))
    recent = await session.scalars(
        statement.order_by(ApplicationEvent.sequence.desc()).limit(limit)
    )
    return list(recent)[::-1]


async def count_application_events(session: AsyncSession, application_id: int) -> int:
    """Return how many events an application has recorded."""

    total = await session.scalar(
        select(func.count())
        .select_from(ApplicationEvent)
        .where(ApplicationEvent.application_id == application_id)
    )
    return int(total or 0)


async def latest_sequences(session: AsyncSession, application_ids: Sequence[int]) -> dict[int, int]:
    """Return the latest event sequence of each application (its revision number)."""

    if not application_ids:
        return {}
    rows = await session.execute(
        select(ApplicationEvent.application_id, func.max(ApplicationEvent.sequence))
        .where(ApplicationEvent.application_id.in_(application_ids))
        .group_by(ApplicationEvent.application_id)
    )
    return {int(application_id): int(sequence) for application_id, sequence in rows.tuples()}

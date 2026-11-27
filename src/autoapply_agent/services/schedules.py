"""Recurring discovery schedules: cadence math, fire / skip / coalesce decisions, history.

A schedule holds the parameters of ``POST /runs`` (query terms, source configs) and a
cadence: every ``interval_minutes`` counted from ``start_at`` (elapsed time, so DST does not
change the spacing), or a five-field cron expression evaluated on the wall clock of
``timezone`` (:mod:`~autoapply_agent.services.cron`). The scheduler
(:class:`~autoapply_agent.services.scheduler.RunScheduler`) calls
:func:`process_due_schedule` every tick; the HTTP API calls :func:`trigger_schedule`,
:func:`pause_schedule` and :func:`resume_schedule`. Every decision appends a
:class:`~autoapply_agent.db.models.RunScheduleEvent`.

* **Claim**: a fire is taken with one conditional ``UPDATE`` (on ``next_run_at`` and
  ``last_run_id``) in the transaction that queues its run, so two ticks or two processes
  never fire it twice; the loser rolls back.
* **Overlap**: while the schedule's last run is queued or running, ``skip`` drops the fire
  (``skipped_overlap``) and ``buffer_one`` keeps one (``buffered``) that starts as soon as
  that run ends; further fires are skipped.
* **Misfires**: fires missed while the scheduler was down are coalesced into one run
  (``coalesced_misfire``); the next fire is the first one after now (no catch-up storm).
* **Pause**: a paused schedule never fires on its own (manual triggers still work);
  resuming continues with the next fire after now, without catching up.
* **Jitter**: every fire is delayed by a deterministic 0-``jitter_seconds`` offset derived
  from the schedule id and the fire time, so schedules on one cadence spread out.

Schedules only queue discovery runs; nothing here applies to jobs or contacts employers.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from itertools import islice
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import ColumnElement, and_, delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from autoapply_agent.core.time import utc_now
from autoapply_agent.db.models import (
    OverlapPolicy,
    Run,
    RunSchedule,
    RunScheduleEvent,
    RunStatus,
    ScheduleEventKind,
    ScheduleKind,
)
from autoapply_agent.services.cron import CronError, CronExpression, load_zone, parse_cron
from autoapply_agent.services.job_export import rfc3339
from autoapply_agent.services.job_search import as_utc
from autoapply_agent.services.runs import enqueue_run

MIN_INTERVAL_MINUTES = 15
"""Politeness floor: no schedule fires more often than every 15 minutes (cron included)."""
MAX_INTERVAL_MINUTES = 43_200
MAX_JITTER_SECONDS = 600
"""Below the 15-minute floor, so jitter never reorders two fires of one schedule."""
MAX_NOTE_CHARS = 500
MAX_REASON_CHARS = 512
DEFAULT_PREVIEW_COUNT = 5
MAX_PREVIEW_COUNT = 20
MAX_COUNTED_MISSES = 1000
MAX_START_AHEAD = timedelta(days=366)
ACTIVE_RUN_STATUSES = frozenset(
    {RunStatus.QUEUED.value, RunStatus.RUNNING.value, RunStatus.CANCEL_REQUESTED.value}
)
TIMING_FIELDS = frozenset(
    {"kind", "interval_minutes", "cron", "timezone", "start_at", "jitter_seconds"}
)


class ScheduleConflictError(Exception):
    """The schedule changed concurrently (another tick, trigger or request); retry."""


def validate_cron(text: str) -> CronExpression:
    """Parse a schedule's cron expression and enforce the politeness floor.

    Args:
        text: Five-field expression or macro.

    Returns:
        Parsed expression.

    Raises:
        CronError: If it is malformed, never fires, or fires more often than every
            :data:`MIN_INTERVAL_MINUTES` minutes.
    """

    expression = parse_cron(text)
    gap = expression.min_gap_minutes
    if gap < MIN_INTERVAL_MINUTES:
        raise CronError(
            f"fires {gap} minute(s) apart; schedules fire at most every "
            f"{MIN_INTERVAL_MINUTES} minutes"
        )
    if expression.next_fire(utc_now(), load_zone("UTC")) is None:
        raise CronError("never fires")
    return expression


@dataclass(frozen=True)
class Cadence:
    """When a schedule fires, before jitter (nominal fire times).

    Attributes:
        start_at: Interval anchor, and the earliest fire of either kind.
        zone: Time zone of cron wall-clock times (and of local times shown to users).
        interval: Interval length, for interval schedules.
        cron: Parsed expression, for cron schedules.
    """

    start_at: datetime
    zone: ZoneInfo
    interval: timedelta | None = None
    cron: CronExpression | None = None

    @classmethod
    def of(cls, schedule: RunSchedule) -> Cadence:
        """Build the cadence of a stored schedule.

        Raises:
            CronError: If the stored expression or time zone is no longer valid here.
        """

        zone = load_zone(schedule.timezone)
        start_at = as_utc(schedule.start_at)
        if schedule.kind == ScheduleKind.INTERVAL.value:
            minutes = max(schedule.interval_minutes or 0, MIN_INTERVAL_MINUTES)
            return cls(start_at, zone, interval=timedelta(minutes=minutes))
        return cls(start_at, zone, cron=parse_cron(schedule.cron or ""))

    def iter_nominal(self, after: datetime, *, inclusive: bool = False) -> Iterator[datetime]:
        """Yield nominal fire instants after ``after`` (or at it when ``inclusive``)."""

        reference = as_utc(after)
        if reference < self.start_at:
            reference, inclusive = self.start_at, True
        if self.cron is not None:
            yield from self.cron.iter_fires(reference, self.zone, inclusive=inclusive)
            return
        if self.interval is None:
            return
        current = self.start_at + (reference - self.start_at) // self.interval * self.interval
        if current < reference or not inclusive:
            current += self.interval
        while True:
            yield current
            current += self.interval

    def next_nominal(self, after: datetime, *, inclusive: bool = False) -> datetime | None:
        """First nominal fire instant after ``after`` (None: never again)."""

        return next(self.iter_nominal(after, inclusive=inclusive), None)


def jitter_offset(schedule_id: int, nominal: datetime, jitter_seconds: int) -> timedelta:
    """Deterministic delay in ``[0, jitter_seconds]`` for one fire of one schedule."""

    if jitter_seconds <= 0:
        return timedelta(0)
    key = f"{schedule_id}:{as_utc(nominal).isoformat()}".encode()
    draw = int.from_bytes(hashlib.sha256(key).digest()[:8], "big")
    return timedelta(seconds=draw % (jitter_seconds + 1))


def _planned(schedule: RunSchedule, nominal: datetime | None) -> datetime | None:
    """Planned fire instant of a nominal one (jitter added)."""

    if nominal is None:
        return None
    return nominal + jitter_offset(schedule.id, nominal, schedule.jitter_seconds)


def plan_next(schedule: RunSchedule, *, after: datetime, inclusive: bool) -> datetime | None:
    """Planned instant of the first fire after ``after`` (or at it when ``inclusive``)."""

    return _planned(schedule, Cadence.of(schedule).next_nominal(after, inclusive=inclusive))


def _nominal_of(cadence: Cadence, planned: datetime, jitter_seconds: int) -> datetime:
    """The nominal fire a planned instant was jittered from.

    Jitter is below the 15-minute floor, so it is the first nominal fire at or after
    ``planned - jitter_seconds``.
    """

    nominal = cadence.next_nominal(planned - timedelta(seconds=jitter_seconds), inclusive=True)
    return nominal if nominal is not None and nominal <= planned else planned


def upcoming_fires(schedule: RunSchedule, count: int = DEFAULT_PREVIEW_COUNT) -> list[datetime]:
    """The next ``count`` planned fire instants (empty while paused).

    Args:
        schedule: Stored schedule.
        count: How many fires to list.

    Returns:
        Increasing aware UTC instants, starting with ``next_run_at``.
    """

    if schedule.paused or schedule.next_run_at is None or count < 1:
        return []
    cadence = Cadence.of(schedule)
    first = as_utc(schedule.next_run_at)
    nominal = _nominal_of(cadence, first, schedule.jitter_seconds)
    fires = [first]
    for following in islice(cadence.iter_nominal(nominal), count - 1):
        fires.append(following + jitter_offset(schedule.id, following, schedule.jitter_seconds))
    return fires


def local_time(instant: datetime, zone: ZoneInfo) -> str:
    """ISO 8601 wall-clock time of ``instant`` in ``zone``, with its UTC offset."""

    return as_utc(instant).astimezone(zone).isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ScheduleFilters:
    """Filters of ``GET /schedules`` and the MCP ``list_schedules`` tool."""

    paused: bool | None = None
    kind: ScheduleKind | None = None
    q: str | None = None


async def list_schedules(
    session: AsyncSession, filters: ScheduleFilters, *, limit: int, offset: int = 0
) -> tuple[int, list[RunSchedule]]:
    """One page of schedules, soonest ``next_run_at`` first (paused ones last).

    Args:
        session: Active async DB session.
        filters: Paused state, kind and case-insensitive name substring.
        limit: Maximum number of schedules.
        offset: Number of matches to skip.

    Returns:
        ``(total matches, page)``.
    """

    conditions: list[ColumnElement[bool]] = []
    if filters.paused is not None:
        conditions.append(RunSchedule.paused.is_(filters.paused))
    if filters.kind is not None:
        conditions.append(RunSchedule.kind == filters.kind.value)
    if filters.q:
        conditions.append(func.lower(RunSchedule.name).contains(filters.q.lower(), autoescape=True))
    total = await session.scalar(select(func.count()).select_from(RunSchedule).where(*conditions))
    rows = await session.scalars(
        select(RunSchedule)
        .where(*conditions)
        .order_by(
            RunSchedule.next_run_at.is_(None), RunSchedule.next_run_at.asc(), RunSchedule.id.asc()
        )
        .offset(offset)
        .limit(limit)
    )
    return int(total or 0), list(rows)


async def schedule_events(
    session: AsyncSession,
    schedule_id: int,
    *,
    kinds: Sequence[ScheduleEventKind] = (),
    limit: int,
    offset: int = 0,
) -> tuple[int, list[RunScheduleEvent]]:
    """One page of a schedule's history, newest first.

    Args:
        session: Active async DB session.
        schedule_id: Schedule identifier.
        kinds: Keep only these event kinds (all when empty).
        limit: Maximum number of events.
        offset: Number of matches to skip.

    Returns:
        ``(total matches, page)``.
    """

    conditions: list[ColumnElement[bool]] = [RunScheduleEvent.schedule_id == schedule_id]
    if kinds:
        conditions.append(RunScheduleEvent.kind.in_([kind.value for kind in kinds]))
    total = await session.scalar(
        select(func.count()).select_from(RunScheduleEvent).where(*conditions)
    )
    rows = await session.scalars(
        select(RunScheduleEvent)
        .where(*conditions)
        .order_by(RunScheduleEvent.id.desc())
        .offset(offset)
        .limit(limit)
    )
    return int(total or 0), list(rows)


async def last_run_status(session: AsyncSession, schedule: RunSchedule) -> str | None:
    """Status of the run the schedule queued last (None when it has not fired)."""

    if schedule.last_run_id is None:
        return None
    return await session.scalar(select(Run.status).where(Run.id == schedule.last_run_id))


async def due_schedule_ids(session: AsyncSession, *, now: datetime, limit: int) -> list[int]:
    """Ids of the schedules a tick can act on at ``now``.

    That is unpaused schedules that are due, and schedules whose buffered fire can start
    because the run it waited for has ended (a paused schedule only holds a buffered fire
    when a manual trigger buffered it). Buffers still waiting are left out, so they never
    fill the batch and keep due schedules from firing.
    """

    run_ended = or_(Run.id.is_(None), Run.status.not_in(list(ACTIVE_RUN_STATUSES)))
    rows = await session.scalars(
        select(RunSchedule.id)
        .outerjoin(Run, Run.id == RunSchedule.last_run_id)
        .where(
            or_(
                and_(RunSchedule.paused.is_(False), RunSchedule.next_run_at <= as_utc(now)),
                and_(RunSchedule.buffered_at.is_not(None), run_ended),
            )
        )
        .order_by(RunSchedule.next_run_at.asc(), RunSchedule.id.asc())
        .limit(limit)
    )
    return list(rows)


# ---------------------------------------------------------------------------
# Configuration changes
# ---------------------------------------------------------------------------


def _add_event(
    session: AsyncSession,
    schedule: RunSchedule,
    kind: ScheduleEventKind,
    *,
    now: datetime,
    run_id: str | None = None,
    scheduled_for: datetime | None = None,
    reason: str | None = None,
    details: dict[str, Any] | None = None,
) -> RunScheduleEvent:
    """Append one history event (flushed with the caller's transaction)."""

    event = RunScheduleEvent(
        schedule_id=schedule.id,
        kind=kind.value,
        run_id=run_id,
        scheduled_for=scheduled_for,
        reason=reason[:MAX_REASON_CHARS] if reason else None,
        details=details or None,
        created_at=now,
    )
    session.add(event)
    return event


def _timestamp(value: datetime | None) -> str | None:
    """RFC 3339 text of an optional instant (for event details)."""

    return rfc3339(value) if value is not None else None


async def create_schedule(
    session: AsyncSession, values: dict[str, Any], *, now: datetime
) -> RunSchedule:
    """Add a schedule and plan its first fire (the caller commits).

    Args:
        session: Active async DB session.
        values: Validated column values (``start_at`` defaults to the next second).
        now: Creation instant.

    Returns:
        The new schedule.

    Raises:
        sqlalchemy.exc.IntegrityError: If the name is taken.
    """

    fields = dict(values)
    if fields.get("start_at") is None:
        # The next whole second: tidy fire times, and still the next tick for intervals.
        fields["start_at"] = (
            now.replace(microsecond=0) + timedelta(seconds=1) if now.microsecond else now
        )
    schedule = RunSchedule(**fields, created_at=now, updated_at=now)
    session.add(schedule)
    await session.flush()
    if schedule.paused:
        _add_event(session, schedule, ScheduleEventKind.PAUSED, now=now, reason=schedule.pause_note)
    else:
        schedule.next_run_at = plan_next(schedule, after=now, inclusive=True)
    schedule.updated_at = now
    await session.flush()
    return schedule


async def update_schedule(
    session: AsyncSession, schedule: RunSchedule, changes: dict[str, Any], *, now: datetime
) -> None:
    """Apply validated changes; a new cadence re-plans the next fire from ``now``.

    Args:
        session: Active async DB session.
        schedule: Schedule to change.
        changes: Column values to set.
        now: Change instant.
    """

    for key, value in changes.items():
        setattr(schedule, key, value)
    if changes:
        schedule.updated_at = now
    if TIMING_FIELDS & changes.keys() and not schedule.paused:
        schedule.next_run_at = plan_next(schedule, after=now, inclusive=True)
    if changes.get("overlap_policy") == OverlapPolicy.SKIP.value:
        schedule.buffered_at = None


async def pause_schedule(
    session: AsyncSession, schedule: RunSchedule, *, note: str | None, now: datetime
) -> RunScheduleEvent | None:
    """Pause a schedule (idempotent; pausing again only replaces a given note).

    Pausing clears ``next_run_at`` and drops a buffered fire. Returns the ``paused``
    event, or None when the schedule was already paused.
    """

    if schedule.paused:
        if note is not None:
            schedule.pause_note = note
            schedule.updated_at = now
        return None
    details = {
        "next_run_at": _timestamp(schedule.next_run_at),
        "dropped_buffered_fire": _timestamp(schedule.buffered_at),
    }
    schedule.paused = True
    schedule.pause_note = note
    schedule.next_run_at = None
    schedule.buffered_at = None
    schedule.updated_at = now
    return _add_event(
        session,
        schedule,
        ScheduleEventKind.PAUSED,
        now=now,
        reason=note,
        details={key: value for key, value in details.items() if value is not None},
    )


async def resume_schedule(
    session: AsyncSession, schedule: RunSchedule, *, note: str | None, now: datetime
) -> RunScheduleEvent | None:
    """Resume a paused schedule from the next fire after ``now`` (no catch-up).

    Returns the ``resumed`` event, or None when the schedule was not paused.
    """

    if not schedule.paused:
        return None
    schedule.paused = False
    schedule.pause_note = None
    schedule.updated_at = now
    schedule.next_run_at = plan_next(schedule, after=now, inclusive=True)
    return _add_event(
        session,
        schedule,
        ScheduleEventKind.RESUMED,
        now=now,
        reason=note,
        details={"next_run_at": _timestamp(schedule.next_run_at)},
    )


async def delete_schedule(session: AsyncSession, schedule: RunSchedule) -> None:
    """Delete a schedule and its history; the runs it queued are kept."""

    await session.execute(
        delete(RunScheduleEvent).where(RunScheduleEvent.schedule_id == schedule.id)
    )
    await session.delete(schedule)


# ---------------------------------------------------------------------------
# Fires
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FireOutcome:
    """What one fire, trigger or buffered start did.

    Attributes:
        schedule_id: Schedule identifier.
        kind: History event kind recorded.
        run_id: Run queued by it (None when skipped or buffered).
        reason: Human-readable explanation (also stored on the event).
    """

    schedule_id: int
    kind: ScheduleEventKind
    run_id: str | None
    reason: str


async def _active_run(session: AsyncSession, schedule: RunSchedule) -> Run | None:
    """The schedule's last run if it is still queued, running or being cancelled."""

    if schedule.last_run_id is None:
        return None
    run = await session.get(Run, schedule.last_run_id, populate_existing=True)
    if run is None or run.status not in ACTIVE_RUN_STATUSES:
        return None
    return run


async def _queue_run(
    session: AsyncSession, schedule: RunSchedule, *, trigger: str, scheduled_for: datetime | None
) -> Run:
    """Queue a run with the schedule's parameters, through the code behind ``POST /runs``."""

    payload: dict[str, object] = {
        "schedule_id": schedule.id,
        "schedule_name": schedule.name,
        "trigger": trigger,
    }
    if scheduled_for is not None:
        payload["scheduled_for"] = rfc3339(scheduled_for)
    return await enqueue_run(
        session,
        query=schedule.query,
        source_config_ids=schedule.source_config_ids,
        message=f"Run queued by schedule {schedule.name!r} ({trigger})",
        payload=payload,
    )


async def _claim(
    session: AsyncSession,
    schedule: RunSchedule,
    values: dict[str, Any],
    *conditions: ColumnElement[bool],
) -> bool:
    """Apply ``values`` only if the row still holds what this decision was based on.

    The ``last_run_id`` the overlap check read is always part of the condition; callers
    add ``next_run_at`` / ``buffered_at`` / ``paused``. ``updated_at`` is kept: it
    records configuration changes, not fires.
    """

    claimed = await session.scalar(
        update(RunSchedule)
        .where(
            RunSchedule.id == schedule.id,
            RunSchedule.last_run_id.is_not_distinct_from(schedule.last_run_id),
            *conditions,
        )
        .values(**values, updated_at=RunSchedule.updated_at)
        .returning(RunSchedule.id)
        .execution_options(synchronize_session=False)
    )
    return claimed is not None


def _count_due(cadence: Cadence, first: datetime, now: datetime) -> tuple[int, datetime]:
    """How many nominal fires lie in ``[first, now]`` (capped), and the latest one."""

    count, latest = 0, first
    for nominal in islice(cadence.iter_nominal(first, inclusive=True), MAX_COUNTED_MISSES):
        if nominal > now:
            break
        count, latest = count + 1, nominal
    return max(count, 1), latest


async def _fire_due(
    session: AsyncSession, schedule: RunSchedule, now: datetime
) -> FireOutcome | None:
    """Fire, buffer or skip a due schedule, then plan its next fire after ``now``."""

    cadence = Cadence.of(schedule)
    planned = as_utc(schedule.next_run_at) if schedule.next_run_at is not None else now
    nominal = _nominal_of(cadence, planned, schedule.jitter_seconds)
    missed, latest = _count_due(cadence, nominal, now)
    values: dict[str, Any] = {"next_run_at": _planned(schedule, cadence.next_nominal(now))}
    details: dict[str, Any] = {
        "planned_at": rfc3339(planned),
        "late_seconds": max(int((now - planned).total_seconds()), 0),
    }
    if missed > 1:
        details["missed_fires"] = missed
        details["latest_scheduled_for"] = rfc3339(latest)
    active = await _active_run(session, schedule)
    buffered = schedule.buffered_at
    run_id: str | None = None
    if active is None:
        run = await _queue_run(session, schedule, trigger="schedule", scheduled_for=nominal)
        run_id = run.id
        values.update(last_run_id=run.id, last_fired_at=now, buffered_at=None)
        kind = ScheduleEventKind.FIRED if missed == 1 else ScheduleEventKind.COALESCED_MISFIRE
        reason = (
            "queued a run"
            if missed == 1
            else f"coalesced {missed}{'+' if missed == MAX_COUNTED_MISSES else ''} missed "
            "fires into one run"
        )
        if buffered is not None:
            details["buffered_fire"] = _timestamp(buffered)
            reason += " (it also covers the buffered fire)"
    elif schedule.overlap_policy == OverlapPolicy.BUFFER_ONE.value and buffered is None:
        values["buffered_at"] = latest
        kind = ScheduleEventKind.BUFFERED
        reason = f"run {active.id} is still {active.status}; one fire waits for it to finish"
    else:
        kind = ScheduleEventKind.SKIPPED_OVERLAP
        reason = (
            f"run {active.id} is still {active.status} (overlap_policy={schedule.overlap_policy}"
        )
        reason += ", a fire is already buffered)" if buffered is not None else ")"
    if active is not None:
        details["active_run_id"] = active.id
    claimed = await _claim(
        session,
        schedule,
        values,
        RunSchedule.paused.is_(False),
        RunSchedule.next_run_at == schedule.next_run_at,
    )
    if not claimed:
        await session.rollback()
        return None
    _add_event(
        session,
        schedule,
        kind,
        now=now,
        run_id=run_id,
        scheduled_for=nominal,
        reason=reason,
        details=details,
    )
    await session.commit()
    return FireOutcome(schedule.id, kind, run_id, reason)


async def _start_buffered(
    session: AsyncSession, schedule: RunSchedule, now: datetime
) -> FireOutcome | None:
    """Start the buffered fire once the run it waited for has finished."""

    if schedule.buffered_at is None or await _active_run(session, schedule) is not None:
        return None
    buffered = as_utc(schedule.buffered_at)
    previous = schedule.last_run_id
    run = await _queue_run(session, schedule, trigger="buffered", scheduled_for=buffered)
    claimed = await _claim(
        session,
        schedule,
        {"buffered_at": None, "last_run_id": run.id, "last_fired_at": now},
        RunSchedule.buffered_at == schedule.buffered_at,
    )
    if not claimed:
        await session.rollback()
        return None
    reason = f"started the buffered fire after run {previous} finished"
    _add_event(
        session,
        schedule,
        ScheduleEventKind.FIRED,
        now=now,
        run_id=run.id,
        scheduled_for=buffered,
        reason=reason,
        details={
            "buffered_fire": rfc3339(buffered),
            "waited_seconds": max(int((now - buffered).total_seconds()), 0),
        },
    )
    await session.commit()
    return FireOutcome(schedule.id, ScheduleEventKind.FIRED, run.id, reason)


async def process_due_schedule(
    session: AsyncSession, schedule_id: int, *, now: datetime
) -> FireOutcome | None:
    """Handle one schedule in its own transaction (committed or rolled back here).

    Args:
        session: Fresh async DB session.
        schedule_id: Schedule picked by :func:`due_schedule_ids`.
        now: Tick instant.

    Returns:
        The outcome, or None when nothing was due or another tick claimed it first.
    """

    schedule = await session.get(RunSchedule, schedule_id, populate_existing=True)
    if schedule is None:
        return None
    due = schedule.next_run_at is not None and as_utc(schedule.next_run_at) <= as_utc(now)
    if due and not schedule.paused:
        return await _fire_due(session, schedule, as_utc(now))
    return await _start_buffered(session, schedule, as_utc(now))


async def trigger_schedule(
    session: AsyncSession, schedule: RunSchedule, *, now: datetime
) -> FireOutcome:
    """Run a schedule now, honouring its overlap policy (works while paused too).

    The regular cadence (``next_run_at``) is unchanged. Commits.

    Raises:
        ScheduleConflictError: If the schedule fired or changed concurrently.
    """

    active = await _active_run(session, schedule)
    run_id: str | None = None
    details: dict[str, Any] = {"trigger": "manual"}
    if active is None:
        run = await _queue_run(session, schedule, trigger="manual", scheduled_for=None)
        run_id = run.id
        kind, reason = ScheduleEventKind.TRIGGERED, "manual trigger queued a run"
        claimed = await _claim(
            session, schedule, {"last_run_id": run.id, "last_fired_at": now, "buffered_at": None}
        )
    elif schedule.overlap_policy == OverlapPolicy.BUFFER_ONE.value and schedule.buffered_at is None:
        kind = ScheduleEventKind.BUFFERED
        reason = (
            f"manual trigger: run {active.id} is still {active.status}; "
            "it starts when that run finishes"
        )
        claimed = await _claim(
            session, schedule, {"buffered_at": now}, RunSchedule.buffered_at.is_(None)
        )
    else:
        kind = ScheduleEventKind.SKIPPED_OVERLAP
        reason = (
            f"manual trigger skipped: run {active.id} is still {active.status} "
            f"(overlap_policy={schedule.overlap_policy}"
        )
        reason += ", a fire is already buffered)" if schedule.buffered_at is not None else ")"
        claimed = True
    if active is not None:
        details["active_run_id"] = active.id
    if not claimed:
        await session.rollback()
        raise ScheduleConflictError("schedule was changed by another request or tick; retry")
    _add_event(session, schedule, kind, now=now, run_id=run_id, reason=reason, details=details)
    await session.commit()
    await session.refresh(schedule)
    return FireOutcome(schedule.id, kind, run_id, reason)

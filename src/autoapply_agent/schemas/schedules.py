"""Pydantic schemas for run schedules (``/schedules``)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_core import PydanticCustomError

from autoapply_agent.core.time import utc_now
from autoapply_agent.db.models import (
    OverlapPolicy,
    RunSchedule,
    RunScheduleEvent,
    RunStatus,
    ScheduleEventKind,
    ScheduleKind,
)
from autoapply_agent.schemas.runs import RunParameters
from autoapply_agent.services.cron import CronError, load_zone
from autoapply_agent.services.job_search import as_utc
from autoapply_agent.services.schedules import (
    MAX_INTERVAL_MINUTES,
    MAX_JITTER_SECONDS,
    MAX_NOTE_CHARS,
    MAX_START_AHEAD,
    MIN_INTERVAL_MINUTES,
    local_time,
    validate_cron,
)

_EARLIEST_START = datetime(1970, 1, 1, tzinfo=UTC)
_NON_NULLABLE_UPDATES = (
    "name",
    "kind",
    "interval_minutes",
    "cron",
    "timezone",
    "start_at",
    "overlap_policy",
    "jitter_seconds",
)


def _clean_text(value: str | None, *, multiline: bool) -> str | None:
    """Strip whitespace (blank becomes None) and refuse control characters."""

    if value is None:
        return None
    allowed = frozenset("\t\n\r") if multiline else frozenset("\t")
    if any((ord(char) < 32 or ord(char) == 127) and char not in allowed for char in value):
        raise PydanticCustomError("text_control_characters", "must not contain control characters")
    return value.strip() or None


def _clean_name(value: str | None) -> str | None:
    """Schedule names: one line, at least two visible characters."""

    if value is None:
        return None
    cleaned = _clean_text(value, multiline=False)
    if cleaned is None or len(cleaned) < 2:
        raise PydanticCustomError("name_too_short", "name needs at least 2 visible characters")
    return cleaned


def _check_cron(value: str | None) -> str | None:
    """Parse the cron expression (normalised) or raise the 422 ``cron_invalid`` error."""

    if value is None:
        return None
    try:
        return validate_cron(value).source
    except CronError as exc:
        raise PydanticCustomError(
            "cron_invalid", "invalid cron expression: {reason}", {"reason": str(exc)}
        ) from None


def _check_timezone(value: str | None) -> str | None:
    """Accept IANA time zone names only."""

    if value is None:
        return None
    try:
        load_zone(value)
    except CronError as exc:
        raise PydanticCustomError("timezone_invalid", "{reason}", {"reason": str(exc)}) from None
    return value


def _check_start(value: datetime | None) -> datetime | None:
    """``start_at`` as aware UTC, from 1970 to one year ahead."""

    if value is None:
        return None
    try:
        instant = as_utc(value)
    except OverflowError:
        raise PydanticCustomError(
            "datetime_utc_range", "Datetime is outside the supported UTC range"
        ) from None
    if instant < _EARLIEST_START or instant > utc_now() + MAX_START_AHEAD:
        raise PydanticCustomError(
            "start_at_range",
            "start_at must be between 1970-01-01 and {days} days from now",
            {"days": MAX_START_AHEAD.days},
        )
    return instant


def _resolve_kind(
    kind: ScheduleKind | None, interval_minutes: int | None, cron: str | None
) -> ScheduleKind:
    """The cadence kind: exactly one of ``interval_minutes`` and ``cron``, matching ``kind``."""

    if interval_minutes is not None and cron is not None:
        raise PydanticCustomError("schedule_cadence", "give interval_minutes or cron, not both")
    if interval_minutes is None and cron is None:
        raise PydanticCustomError(
            "schedule_cadence",
            "give interval_minutes (every N minutes) or cron (a five-field expression)",
        )
    inferred = ScheduleKind.CRON if cron is not None else ScheduleKind.INTERVAL
    if kind is not None and kind is not inferred:
        needed = "cron" if kind is ScheduleKind.CRON else "interval_minutes"
        raise PydanticCustomError(
            "schedule_cadence", "kind={kind} needs {needed}", {"kind": kind.value, "needed": needed}
        )
    return inferred


_NAME_FIELD = Field(min_length=2, max_length=120, description="Unique schedule name.")
_INTERVAL_DESCRIPTION = (
    f"Fire every N minutes ({MIN_INTERVAL_MINUTES}-{MAX_INTERVAL_MINUTES}), counted from "
    "start_at in elapsed time."
)
_CRON_DESCRIPTION = (
    "Five-field cron expression (minute hour day-of-month month day-of-week) or a macro "
    f"such as @daily, evaluated in timezone; fires at least {MIN_INTERVAL_MINUTES} minutes apart."
)
_START_DESCRIPTION = (
    "Interval anchor and earliest fire (default: now, so an interval schedule fires on "
    "the next tick); up to one year ahead."
)
_JITTER_DESCRIPTION = (
    f"Delay each fire by a deterministic 0-N seconds (N <= {MAX_JITTER_SECONDS}) so "
    "schedules on one cadence spread out."
)


class ScheduleCreate(RunParameters):
    """Create a schedule (``POST /schedules``): run parameters plus a cadence."""

    model_config = ConfigDict(extra="forbid")

    name: str = _NAME_FIELD
    kind: ScheduleKind | None = Field(
        default=None, description="interval or cron; inferred from interval_minutes / cron."
    )
    interval_minutes: int | None = Field(
        default=None,
        ge=MIN_INTERVAL_MINUTES,
        le=MAX_INTERVAL_MINUTES,
        description=_INTERVAL_DESCRIPTION,
    )
    cron: str | None = Field(default=None, max_length=120, description=_CRON_DESCRIPTION)
    timezone: str = Field(
        default="UTC", max_length=64, description="IANA time zone of cron wall-clock times."
    )
    start_at: datetime | None = Field(default=None, description=_START_DESCRIPTION)
    overlap_policy: OverlapPolicy = Field(
        default=OverlapPolicy.SKIP,
        description="skip: drop a fire while the last run is active; buffer_one: keep one.",
    )
    jitter_seconds: int = Field(
        default=0, ge=0, le=MAX_JITTER_SECONDS, description=_JITTER_DESCRIPTION
    )
    paused: bool = Field(default=False, description="Create the schedule paused.")
    pause_note: str | None = Field(
        default=None, max_length=MAX_NOTE_CHARS, description="Why it is paused (paused=true)."
    )

    @field_validator("name")
    @classmethod
    def _name(cls, value: str) -> str | None:
        return _clean_name(value)

    @field_validator("cron")
    @classmethod
    def _cron(cls, value: str | None) -> str | None:
        return _check_cron(value)

    @field_validator("timezone")
    @classmethod
    def _timezone(cls, value: str) -> str | None:
        return _check_timezone(value)

    @field_validator("start_at")
    @classmethod
    def _start(cls, value: datetime | None) -> datetime | None:
        return _check_start(value)

    @field_validator("pause_note")
    @classmethod
    def _note(cls, value: str | None) -> str | None:
        return _clean_text(value, multiline=True)

    @model_validator(mode="after")
    def _cadence(self) -> ScheduleCreate:
        self.kind = _resolve_kind(self.kind, self.interval_minutes, self.cron)
        if self.pause_note is not None and not self.paused:
            raise PydanticCustomError("pause_note_unpaused", "pause_note needs paused=true")
        return self

    def to_values(self) -> dict[str, Any]:
        """Column values of the new schedule."""

        kind = self.kind or _resolve_kind(None, self.interval_minutes, self.cron)
        return {
            "name": self.name,
            "query": self.query,
            "source_config_ids": self.source_config_ids,
            "kind": kind.value,
            "interval_minutes": self.interval_minutes,
            "cron": self.cron,
            "timezone": self.timezone,
            "start_at": self.start_at,
            "overlap_policy": self.overlap_policy.value,
            "jitter_seconds": self.jitter_seconds,
            "paused": self.paused,
            "pause_note": self.pause_note,
        }


class ScheduleUpdate(RunParameters):
    """Change a schedule (``PATCH /schedules/{id}``); omitted fields are kept.

    Setting ``cron`` switches the schedule to cron and setting ``interval_minutes``
    switches it to interval. ``query: null`` clears the query and
    ``source_config_ids: null`` means every enabled source. A new cadence re-plans the
    next fire from now. Pause and resume have their own endpoints.
    """

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=2, max_length=120)
    kind: ScheduleKind | None = Field(
        default=None, description="Must match the cadence field sent with it."
    )
    interval_minutes: int | None = Field(
        default=None,
        ge=MIN_INTERVAL_MINUTES,
        le=MAX_INTERVAL_MINUTES,
        description=_INTERVAL_DESCRIPTION,
    )
    cron: str | None = Field(default=None, max_length=120, description=_CRON_DESCRIPTION)
    timezone: str | None = Field(default=None, max_length=64)
    start_at: datetime | None = Field(default=None, description=_START_DESCRIPTION)
    overlap_policy: OverlapPolicy | None = None
    jitter_seconds: int | None = Field(
        default=None, ge=0, le=MAX_JITTER_SECONDS, description=_JITTER_DESCRIPTION
    )

    @field_validator("name")
    @classmethod
    def _name(cls, value: str | None) -> str | None:
        return _clean_name(value)

    @field_validator("cron")
    @classmethod
    def _cron(cls, value: str | None) -> str | None:
        return _check_cron(value)

    @field_validator("timezone")
    @classmethod
    def _timezone(cls, value: str | None) -> str | None:
        return _check_timezone(value)

    @field_validator("start_at")
    @classmethod
    def _start(cls, value: datetime | None) -> datetime | None:
        return _check_start(value)

    @model_validator(mode="after")
    def _consistent(self) -> ScheduleUpdate:
        for field in _NON_NULLABLE_UPDATES:
            if field in self.model_fields_set and getattr(self, field) is None:
                raise PydanticCustomError(
                    "null_not_allowed", "{field} cannot be null", {"field": field}
                )
        if self.kind is not None or (self.interval_minutes is not None and self.cron is not None):
            _resolve_kind(self.kind, self.interval_minutes, self.cron)
        return self

    def to_changes(self) -> dict[str, Any]:
        """Column values to set."""

        changes: dict[str, Any] = {
            field: getattr(self, field)
            for field in self.model_fields_set
            if field not in {"kind", "overlap_policy"}
        }
        if self.overlap_policy is not None:
            changes["overlap_policy"] = self.overlap_policy.value
        if self.cron is not None:
            changes.update(kind=ScheduleKind.CRON.value, interval_minutes=None)
        elif self.interval_minutes is not None:
            changes.update(kind=ScheduleKind.INTERVAL.value, cron=None)
        return changes


class ScheduleNoteRequest(BaseModel):
    """Optional note for pause / resume (``POST /schedules/{id}/pause``)."""

    model_config = ConfigDict(extra="forbid")

    note: str | None = Field(
        default=None, max_length=MAX_NOTE_CHARS, description="Recorded in the history."
    )

    @field_validator("note")
    @classmethod
    def _note(cls, value: str | None) -> str | None:
        return _clean_text(value, multiline=True)


class UpcomingFireRead(BaseModel):
    """One planned fire: the UTC instant and the schedule's local wall-clock time."""

    at: datetime
    local: str = Field(description="ISO 8601 local time with UTC offset, in the time zone.")


def _utc(value: datetime | None) -> datetime | None:
    return as_utc(value) if value is not None else None


class ScheduleRead(BaseModel):
    """A run schedule."""

    id: int
    name: str
    kind: ScheduleKind
    interval_minutes: int | None
    cron: str | None
    timezone: str
    start_at: datetime
    query: str | None
    source_config_ids: list[int] | None
    overlap_policy: OverlapPolicy
    jitter_seconds: int
    paused: bool
    pause_note: str | None
    next_run_at: datetime | None = Field(description="Planned next fire (null while paused).")
    buffered_fire_at: datetime | None = Field(
        description="Fire waiting for the active run (buffer_one)."
    )
    last_fired_at: datetime | None
    last_run_id: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_record(cls, schedule: RunSchedule) -> ScheduleRead:
        """Build the response from the stored schedule."""

        return cls(**_record_fields(schedule))


def _record_fields(schedule: RunSchedule) -> dict[str, Any]:
    return {
        "id": schedule.id,
        "name": schedule.name,
        "kind": ScheduleKind(schedule.kind),
        "interval_minutes": schedule.interval_minutes,
        "cron": schedule.cron,
        "timezone": schedule.timezone,
        "start_at": as_utc(schedule.start_at),
        "query": schedule.query,
        "source_config_ids": schedule.source_config_ids,
        "overlap_policy": OverlapPolicy(schedule.overlap_policy),
        "jitter_seconds": schedule.jitter_seconds,
        "paused": schedule.paused,
        "pause_note": schedule.pause_note,
        "next_run_at": _utc(schedule.next_run_at),
        "buffered_fire_at": _utc(schedule.buffered_at),
        "last_fired_at": _utc(schedule.last_fired_at),
        "last_run_id": schedule.last_run_id,
        "created_at": as_utc(schedule.created_at),
        "updated_at": as_utc(schedule.updated_at),
    }


class ScheduleDetailRead(ScheduleRead):
    """A schedule with the status of its last run and its next planned fires."""

    last_run_status: RunStatus | None
    upcoming: list[UpcomingFireRead] = Field(description="Next planned fires (empty if paused).")

    @classmethod
    def from_schedule(
        cls, schedule: RunSchedule, *, upcoming: list[datetime], last_run_status: str | None
    ) -> ScheduleDetailRead:
        """Build the detailed response."""

        zone = load_zone(schedule.timezone) if upcoming else None
        return cls(
            **_record_fields(schedule),
            last_run_status=RunStatus(last_run_status) if last_run_status else None,
            upcoming=[
                UpcomingFireRead(at=at, local=local_time(at, zone))
                for at in upcoming
                if zone is not None
            ],
        )


class ScheduleEventRead(BaseModel):
    """One entry of a schedule's append-only history."""

    id: int
    schedule_id: int
    kind: ScheduleEventKind
    run_id: str | None
    scheduled_for: datetime | None = Field(description="Nominal fire time it is about.")
    reason: str | None
    details: dict[str, Any] | None
    created_at: datetime

    @classmethod
    def from_record(cls, event: RunScheduleEvent) -> ScheduleEventRead:
        """Build the response from the stored event."""

        return cls(
            id=event.id,
            schedule_id=event.schedule_id,
            kind=ScheduleEventKind(event.kind),
            run_id=event.run_id,
            scheduled_for=_utc(event.scheduled_for),
            reason=event.reason,
            details=event.details if isinstance(event.details, dict) else None,
            created_at=as_utc(event.created_at),
        )


class ScheduleTriggerRead(BaseModel):
    """Result of ``POST /schedules/{id}/trigger``."""

    outcome: ScheduleEventKind = Field(description="triggered, buffered or skipped_overlap.")
    run_id: str | None = Field(description="Run queued now (null unless triggered).")
    reason: str
    schedule: ScheduleRead


class CronPreviewRead(BaseModel):
    """Dry run of a cron expression (``GET /schedules/preview``)."""

    cron: str
    timezone: str
    min_gap_minutes: int = Field(description="Smallest wall-clock gap between fires.")
    upcoming: list[UpcomingFireRead]

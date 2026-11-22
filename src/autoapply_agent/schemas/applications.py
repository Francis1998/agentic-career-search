"""Pydantic schemas for the application tracker endpoints (``/applications``)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from autoapply_agent.core.time import utc_now
from autoapply_agent.db.models import SQLITE_MAX_INTEGER, Application, ApplicationEvent, Job
from autoapply_agent.services.application_stages import ApplicationStage, allowed_next_stages
from autoapply_agent.services.application_tracker import (
    MAX_EVENT_NOTE_CHARS,
    MAX_NEXT_ACTION_CHARS,
    MAX_NOTES_CHARS,
    UNSET,
    ApplicationEventType,
    ApplicationPatch,
    FollowUpStatus,
    days_in_stage,
    follow_up_status,
)
from autoapply_agent.services.job_export import safe_http_url
from autoapply_agent.services.job_search import as_utc, is_remote_location

_MULTILINE_ALLOWED = frozenset("\t\n\r")


def _clean_text(value: str | None, *, multiline: bool) -> str | None:
    """Strip surrounding whitespace, map blank text to None and refuse control characters.

    Control characters (NUL included, which PostgreSQL text columns reject) are not
    accepted anywhere; line breaks and tabs are allowed in multi-line fields only, and
    tabs in single-line ones.
    """

    if value is None:
        return None
    allowed = _MULTILINE_ALLOWED if multiline else frozenset("\t")
    if any((ord(char) < 32 or ord(char) == 127) and char not in allowed for char in value):
        kind = "control characters" if multiline else "line breaks or control characters"
        raise ValueError(f"must not contain {kind}")
    stripped = value.strip()
    return stripped or None


def _utc_instant(value: datetime | None) -> datetime | None:
    """Convert a datetime to aware UTC (naive values are UTC), within the supported range."""

    if value is None:
        return None
    try:
        return as_utc(value)
    except OverflowError:
        raise ValueError("datetime is outside the supported UTC range") from None


def _not_in_future(value: datetime | None) -> datetime | None:
    """Refuse an ``applied_at`` later than now."""

    if value is not None and value > utc_now():
        raise ValueError("applied_at cannot be in the future")
    return value


class ApplicationCreate(BaseModel):
    """Start tracking a captured job (``POST /applications``)."""

    model_config = ConfigDict(extra="forbid")

    job_id: int = Field(ge=1, le=SQLITE_MAX_INTEGER, description="Captured job to track.")
    stage: ApplicationStage = Field(
        default=ApplicationStage.SAVED,
        description="Starting stage; applied starts the applied clock (applied_at = now).",
    )
    notes: str | None = Field(
        default=None, max_length=MAX_NOTES_CHARS, description="Editable scratchpad text."
    )
    note: str | None = Field(
        default=None,
        max_length=MAX_EVENT_NOTE_CHARS,
        description="Note recorded with the first timeline event.",
    )
    applied_at: datetime | None = Field(
        default=None, description="When the application was sent (not in the future)."
    )
    next_action_at: datetime | None = Field(
        default=None, description="Follow-up date-time (ISO-8601; naive means UTC)."
    )
    next_action: str | None = Field(
        default=None,
        max_length=MAX_NEXT_ACTION_CHARS,
        description="What to do at next_action_at, e.g. 'Email the recruiter'.",
    )

    @field_validator("notes", "note")
    @classmethod
    def _multiline_text(cls, value: str | None) -> str | None:
        return _clean_text(value, multiline=True)

    @field_validator("next_action")
    @classmethod
    def _single_line_text(cls, value: str | None) -> str | None:
        return _clean_text(value, multiline=False)

    @field_validator("next_action_at")
    @classmethod
    def _utc_next_action(cls, value: datetime | None) -> datetime | None:
        return _utc_instant(value)

    @field_validator("applied_at")
    @classmethod
    def _utc_applied(cls, value: datetime | None) -> datetime | None:
        return _not_in_future(_utc_instant(value))


class ApplicationUpdate(BaseModel):
    """Move, annotate or reschedule an application (``PATCH /applications/{id}``).

    Omitted fields are left alone; ``null`` clears ``notes``, ``applied_at``,
    ``next_action_at`` or ``next_action``. Clearing ``next_action_at`` also clears
    ``next_action`` unless the same request sets it.
    """

    model_config = ConfigDict(extra="forbid")

    stage: ApplicationStage | None = Field(
        default=None, description="Target stage; must be a legal next stage (409 otherwise)."
    )
    note: str | None = Field(
        default=None,
        max_length=MAX_EVENT_NOTE_CHARS,
        description="Timeline note recorded with this change (or on its own).",
    )
    notes: str | None = Field(
        default=None, max_length=MAX_NOTES_CHARS, description="Replace the scratchpad text."
    )
    applied_at: datetime | None = Field(
        default=None, description="When the application was sent (not in the future)."
    )
    next_action_at: datetime | None = Field(default=None, description="Follow-up date-time.")
    next_action: str | None = Field(
        default=None, max_length=MAX_NEXT_ACTION_CHARS, description="Follow-up label."
    )

    @field_validator("notes", "note")
    @classmethod
    def _multiline_text(cls, value: str | None) -> str | None:
        return _clean_text(value, multiline=True)

    @field_validator("next_action")
    @classmethod
    def _single_line_text(cls, value: str | None) -> str | None:
        return _clean_text(value, multiline=False)

    @field_validator("next_action_at")
    @classmethod
    def _utc_next_action(cls, value: datetime | None) -> datetime | None:
        return _utc_instant(value)

    @field_validator("applied_at")
    @classmethod
    def _utc_applied(cls, value: datetime | None) -> datetime | None:
        return _not_in_future(_utc_instant(value))

    @model_validator(mode="after")
    def _has_a_field(self) -> ApplicationUpdate:
        if not self.model_fields_set:
            raise ValueError(
                "provide at least one of stage, note, notes, applied_at, next_action_at, "
                "next_action"
            )
        return self

    def to_patch(self) -> ApplicationPatch:
        """Translate the request into a service patch (unsent fields stay unset)."""

        sent = self.model_fields_set
        return ApplicationPatch(
            stage=self.stage,
            note=self.note,
            notes=self.notes if "notes" in sent else UNSET,
            applied_at=self.applied_at if "applied_at" in sent else UNSET,
            next_action_at=self.next_action_at if "next_action_at" in sent else UNSET,
            next_action=self.next_action if "next_action" in sent else UNSET,
        )


class ApplicationArchiveRequest(BaseModel):
    """Optional body of the archive and unarchive endpoints."""

    model_config = ConfigDict(extra="forbid")

    note: str | None = Field(
        default=None, max_length=MAX_EVENT_NOTE_CHARS, description="Timeline note."
    )

    @field_validator("note")
    @classmethod
    def _multiline_text(cls, value: str | None) -> str | None:
        return _clean_text(value, multiline=True)


def _priority_tier(job: Job) -> str | None:
    """Priority tier recorded in the job's decision trace, if any."""

    raw = job.raw if isinstance(job.raw, dict) else {}
    decision = raw.get("agent_decision")
    tier = decision.get("priority_tier") if isinstance(decision, dict) else None
    return tier if isinstance(tier, str) else None


class ApplicationJobSummary(BaseModel):
    """The tracked job, as captured by a discovery run."""

    id: int
    title: str
    company: str | None
    location: str | None
    remote: bool
    url: str | None = Field(description="Posting link; null unless it is an http(s) URL.")
    score: float
    priority_tier: str | None
    run_id: str
    captured_at: datetime

    @classmethod
    def from_job(cls, job: Job) -> ApplicationJobSummary:
        """Summarize a persisted job."""

        return cls(
            id=job.id,
            title=job.title,
            company=job.company,
            location=job.location,
            remote=is_remote_location(job.location),
            url=safe_http_url(job.url),
            score=job.score,
            priority_tier=_priority_tier(job),
            run_id=job.run_id,
            captured_at=as_utc(job.created_at),
        )


class ApplicationRead(BaseModel):
    """A tracked application with its follow-up state and job summary."""

    id: int
    job_id: int
    stage: ApplicationStage
    archived: bool
    notes: str | None
    applied_at: datetime | None
    next_action_at: datetime | None
    next_action: str | None
    follow_up_status: FollowUpStatus = Field(
        description="overdue, due (within 7 days), scheduled (later) or none."
    )
    days_in_stage: int = Field(description="Whole days since the current stage was entered.")
    stage_changed_at: datetime
    allowed_stages: list[ApplicationStage] = Field(
        description="Legal next stages from the state machine (empty when final)."
    )
    created_at: datetime
    updated_at: datetime
    job: ApplicationJobSummary

    @classmethod
    def from_records(cls, application: Application, job: Job, *, now: datetime) -> ApplicationRead:
        """Build the API view of an application at time ``now``."""

        stage = ApplicationStage(application.stage)
        return cls(
            id=application.id,
            job_id=application.job_id,
            stage=stage,
            archived=application.archived,
            notes=application.notes,
            applied_at=as_utc(application.applied_at) if application.applied_at else None,
            next_action_at=(
                as_utc(application.next_action_at) if application.next_action_at else None
            ),
            next_action=application.next_action,
            follow_up_status=follow_up_status(application.next_action_at, now),
            days_in_stage=days_in_stage(application, now),
            stage_changed_at=as_utc(application.stage_changed_at),
            allowed_stages=list(allowed_next_stages(stage)),
            created_at=as_utc(application.created_at),
            updated_at=as_utc(application.updated_at),
            job=ApplicationJobSummary.from_job(job),
        )


class ApplicationEventRead(BaseModel):
    """One entry of an application's append-only timeline."""

    id: int
    application_id: int
    sequence: int
    event_type: ApplicationEventType
    from_stage: ApplicationStage | None
    to_stage: ApplicationStage | None
    note: str | None
    changes: dict[str, Any] = Field(
        description="Changed fields as {field: {from, to}}; job_id and initial values on tracked."
    )
    created_at: datetime

    @classmethod
    def from_record(cls, event: ApplicationEvent) -> ApplicationEventRead:
        """Build the API view of a persisted event."""

        return cls(
            id=event.id,
            application_id=event.application_id,
            sequence=event.sequence,
            event_type=ApplicationEventType(event.event_type),
            from_stage=ApplicationStage(event.from_stage) if event.from_stage else None,
            to_stage=ApplicationStage(event.to_stage) if event.to_stage else None,
            note=event.note,
            changes=event.changes if isinstance(event.changes, dict) else {},
            created_at=as_utc(event.created_at),
        )


class BoardColumnRead(BaseModel):
    """One stage column of the board."""

    stage: ApplicationStage
    count: int = Field(description="Applications in this stage that match the filters.")
    applications: list[ApplicationRead] = Field(description="The first per_stage of them.")


class ApplicationBoardRead(BaseModel):
    """Applications grouped by stage, in pipeline order."""

    total: int
    include_archived: bool
    follow_ups: dict[str, int] = Field(
        description="Matching applications per follow_up_status (overdue, due, scheduled, none)."
    )
    columns: list[BoardColumnRead]

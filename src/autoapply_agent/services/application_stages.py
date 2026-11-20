"""Application stage state machine and an in-process stage tracker (CRM-lite pipeline).

Tracks job applications through saved → applied → interview → offer →
rejected/accepted with explicit allowed transitions. The transition rules here are
the single state machine of the project: :class:`ApplicationStageTracker` keeps
records in memory, and the persistent tracker behind ``/applications``
(:mod:`autoapply_agent.services.application_tracker`) stores them in the database.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum


class ApplicationStage(StrEnum):
    """Pipeline stage for a tracked job application."""

    SAVED = "saved"
    APPLIED = "applied"
    INTERVIEW = "interview"
    OFFER = "offer"
    REJECTED = "rejected"
    ACCEPTED = "accepted"


_FORWARD: dict[ApplicationStage, ApplicationStage] = {
    ApplicationStage.SAVED: ApplicationStage.APPLIED,
    ApplicationStage.APPLIED: ApplicationStage.INTERVIEW,
    ApplicationStage.INTERVIEW: ApplicationStage.OFFER,
    ApplicationStage.OFFER: ApplicationStage.ACCEPTED,
}

_ALLOWED: dict[ApplicationStage, frozenset[ApplicationStage]] = {
    ApplicationStage.SAVED: frozenset({ApplicationStage.APPLIED, ApplicationStage.REJECTED}),
    ApplicationStage.APPLIED: frozenset({ApplicationStage.INTERVIEW, ApplicationStage.REJECTED}),
    ApplicationStage.INTERVIEW: frozenset({ApplicationStage.OFFER, ApplicationStage.REJECTED}),
    ApplicationStage.OFFER: frozenset({ApplicationStage.ACCEPTED, ApplicationStage.REJECTED}),
    ApplicationStage.REJECTED: frozenset(),
    ApplicationStage.ACCEPTED: frozenset(),
}


@dataclass(slots=True, frozen=True)
class ApplicationRecord:
    """Snapshot of a tracked application."""

    job_key: str
    stage: ApplicationStage
    note: str | None
    updated_at: str


PIPELINE_ORDER: tuple[ApplicationStage, ...] = (
    ApplicationStage.SAVED,
    ApplicationStage.APPLIED,
    ApplicationStage.INTERVIEW,
    ApplicationStage.OFFER,
    ApplicationStage.ACCEPTED,
    ApplicationStage.REJECTED,
)
"""Board column order: the forward path, then the two terminal stages."""


class ApplicationStageError(ValueError):
    """Raised when a stage transition is not allowed."""


def allowed_next_stages(stage: ApplicationStage) -> tuple[ApplicationStage, ...]:
    """Return the legal next stages of ``stage`` in pipeline order.

    Args:
        stage: Current stage.

    Returns:
        Stages a record in ``stage`` may move to (empty for terminal stages).
    """

    return tuple(candidate for candidate in PIPELINE_ORDER if candidate in _ALLOWED[stage])


def check_transition(current: ApplicationStage, target: ApplicationStage) -> None:
    """Validate moving a record from ``current`` to ``target``.

    Staying in the same stage is always allowed (it is not a transition).

    Args:
        current: Stage the record is in.
        target: Requested stage.

    Raises:
        ApplicationStageError: If ``target`` is not a legal next stage of ``current``.
    """

    if target == current or target in _ALLOWED[current]:
        return
    allowed = ", ".join(stage.value for stage in allowed_next_stages(current))
    reason = f"allowed: {allowed}" if allowed else f"{current.value} is a final stage"
    raise ApplicationStageError(f"cannot move from {current.value} to {target.value} ({reason})")


class ApplicationStageTracker:
    """In-memory CRM-lite tracker for application pipeline stages."""

    def __init__(self) -> None:
        """Initialize an empty tracker."""

        self._records: dict[str, ApplicationRecord] = {}

    def upsert(
        self,
        job_key: str,
        stage: ApplicationStage,
        *,
        note: str | None = None,
    ) -> ApplicationRecord:
        """Create or move a job into an explicit stage.

        Args:
            job_key: Stable job identifier (URL or internal id).
            stage: Target pipeline stage.
            note: Optional operator note.

        Returns:
            Updated ApplicationRecord.

        Raises:
            ApplicationStageError: If transitioning from an existing stage
                to an illegal target.
            ValueError: If job_key is empty.
        """

        key = job_key.strip()
        if not key:
            raise ValueError("job_key must be non-empty")
        existing = self._records.get(key)
        if existing is not None:
            try:
                check_transition(existing.stage, stage)
            except ApplicationStageError as exc:
                raise ApplicationStageError(f"{key}: {exc}") from None
        record = ApplicationRecord(
            job_key=key,
            stage=stage,
            note=note,
            updated_at=datetime.now(UTC).isoformat(),
        )
        self._records[key] = record
        return record

    def advance(self, job_key: str, *, note: str | None = None) -> ApplicationRecord:
        """Advance a job along the default forward path.

        Args:
            job_key: Stable job identifier.
            note: Optional operator note.

        Returns:
            Updated ApplicationRecord.

        Raises:
            KeyError: If the job is not tracked.
            ApplicationStageError: If no forward transition exists.
        """

        key = job_key.strip()
        existing = self._records.get(key)
        if existing is None:
            raise KeyError(f"unknown job_key: {key}")
        nxt = _FORWARD.get(existing.stage)
        if nxt is None:
            raise ApplicationStageError(f"no forward transition from {existing.stage.value}")
        return self.upsert(key, nxt, note=note)

    def get(self, job_key: str) -> ApplicationRecord | None:
        """Return the current record for a job, if any."""

        return self._records.get(job_key.strip())

    def list_by_stage(self, stage: ApplicationStage) -> list[ApplicationRecord]:
        """List all records currently in the given stage."""

        return [r for r in self._records.values() if r.stage is stage]

    @staticmethod
    def allowed_transitions(stage: ApplicationStage) -> frozenset[ApplicationStage]:
        """Return legal next stages from ``stage``."""

        return _ALLOWED[stage]

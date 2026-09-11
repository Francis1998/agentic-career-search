"""HITL interview schedule conflict guard (local overlap advisory; never writes calendars).

Closes the gap vs Teal/Huntr calendar sync that auto-writes events. This guard
only detects offline interval overlaps for human review — it never creates,
updates, or deletes calendar events, and never performs network I/O.

Distinct from ``InterviewPrepBriefService`` (prep questions; never schedules)
and ``InterviewFeedbackSynthesizer`` (post-interview debriefs).

Optional later polish via GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2
must stay advisory.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True, frozen=True)
class InterviewSlot:
    """A candidate interview (or busy) window expressed as ISO datetimes."""

    start_iso: str
    end_iso: str
    label: str


@dataclass(slots=True, frozen=True)
class ConflictReport:
    """Human-reviewable conflict advisory (never mutates calendars)."""

    proposed: InterviewSlot
    conflicts: list[InterviewSlot]
    has_conflict: bool
    requires_human_review: bool
    calendar_mutated: bool


class InterviewScheduleConflictGuard:
    """Detect overlapping interview slots offline (HITL; no calendar writes)."""

    def check(
        self,
        *,
        proposed: InterviewSlot,
        existing: Sequence[InterviewSlot],
    ) -> ConflictReport:
        """Return conflicts between ``proposed`` and ``existing`` slots.

        Args:
            proposed: Candidate interview window to evaluate.
            existing: Already-known busy / interview windows.

        Returns:
            ConflictReport with ``requires_human_review=True`` and
            ``calendar_mutated=False``. ``has_conflict`` is True iff any
            existing slot overlaps the proposed range.

        Raises:
            ValueError: If any slot has blank fields or ``end <= start``.
        """

        proposed_norm = _normalize_slot(proposed, field="proposed")
        conflicts: list[InterviewSlot] = []
        proposed_start, proposed_end = _parse_range(proposed_norm)

        for index, slot in enumerate(existing or ()):
            existing_norm = _normalize_slot(slot, field=f"existing[{index}]")
            other_start, other_end = _parse_range(existing_norm)
            if _overlaps(proposed_start, proposed_end, other_start, other_end):
                conflicts.append(existing_norm)

        return ConflictReport(
            proposed=proposed_norm,
            conflicts=conflicts,
            has_conflict=bool(conflicts),
            requires_human_review=True,
            calendar_mutated=False,
        )


def _normalize_slot(slot: InterviewSlot, *, field: str) -> InterviewSlot:
    if not isinstance(slot, InterviewSlot):
        raise ValueError(f"{field} must be an InterviewSlot")
    start_iso = (slot.start_iso or "").strip()
    end_iso = (slot.end_iso or "").strip()
    label = (slot.label or "").strip()
    if not start_iso:
        raise ValueError(f"{field}.start_iso must be a non-empty ISO datetime")
    if not end_iso:
        raise ValueError(f"{field}.end_iso must be a non-empty ISO datetime")
    if not label:
        raise ValueError(f"{field}.label must be a non-empty string")
    return InterviewSlot(start_iso=start_iso, end_iso=end_iso, label=label)


def _parse_iso(value: str, *, field: str) -> datetime:
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field} must be a valid ISO datetime") from exc


def _parse_range(slot: InterviewSlot) -> tuple[datetime, datetime]:
    start = _parse_iso(slot.start_iso, field="start_iso")
    end = _parse_iso(slot.end_iso, field="end_iso")
    if end <= start:
        raise ValueError("end_iso must be after start_iso")
    return start, end


def _overlaps(
    start_a: datetime,
    end_a: datetime,
    start_b: datetime,
    end_b: datetime,
) -> bool:
    # Half-open style: touching endpoints (end == start) are not conflicts.
    return start_a < end_b and start_b < end_a

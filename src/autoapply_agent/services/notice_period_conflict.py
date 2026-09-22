"""HITL notice-period conflict flagger (offline; never auto-accepts).

Closes the gap vs Huntr / Teal / Greenhouse start-date planners locked in
closed UIs. Given contractual notice weeks and preferred start delay days,
emits conflict bands — never auto-accepts offers and never performs network
I/O.

Distinct from ``InterviewScheduleConflictGuard`` (interview slot overlaps) and
``OfferDeadlineTracker`` (acceptance deadlines). Optional later polish via
GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class NoticePeriodConflictReport:
    """Human-reviewable notice vs preferred-start conflict report."""

    notice_weeks: float
    preferred_start_days: float
    notice_days: float
    slack_days: float
    conflict_band: str
    guidance: list[str]
    requires_human_review: bool
    auto_accept: bool


class NoticePeriodConflictFlagger:
    """Flag conflicts between notice period and preferred start delay."""

    def flag(
        self,
        *,
        notice_weeks: float,
        preferred_start_days: float,
    ) -> NoticePeriodConflictReport:
        """Compute notice vs preferred-start conflict band.

        Args:
            notice_weeks: Contractual notice in weeks (``>= 0``).
            preferred_start_days: Days until preferred start (``>= 0``).

        Returns:
            NoticePeriodConflictReport with ``auto_accept=False``.

        Raises:
            ValueError: On invalid numeric inputs.
        """

        if notice_weeks < 0:
            raise ValueError("notice_weeks must be >= 0")
        if preferred_start_days < 0:
            raise ValueError("preferred_start_days must be >= 0")

        notice_days = notice_weeks * 7.0
        slack = preferred_start_days - notice_days

        if slack >= 14:
            band = "comfortable"
        elif slack >= 0:
            band = "tight"
        elif slack >= -14:
            band = "conflict"
        else:
            band = "hard_conflict"

        guidance = [
            "Notice math is advisory; confirm with current employer policy.",
            "Do not auto-accept from this flagger.",
        ]
        if band == "comfortable":
            guidance.append("Preferred start leaves comfortable slack after notice.")
        elif band == "tight":
            guidance.append("Start is feasible but tight; align PTO/garden leave.")
        elif band == "conflict":
            guidance.append("Preferred start is before notice ends; negotiate start or buyout.")
        else:
            guidance.append(
                "Hard conflict: preferred start is far before notice clearance; "
                "request delayed start or notice buyout."
            )

        return NoticePeriodConflictReport(
            notice_weeks=float(notice_weeks),
            preferred_start_days=float(preferred_start_days),
            notice_days=float(notice_days),
            slack_days=float(slack),
            conflict_band=band,
            guidance=guidance,
            requires_human_review=True,
            auto_accept=False,
        )

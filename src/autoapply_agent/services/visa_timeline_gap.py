"""HITL VisaTimelineGapAdvisor (offline; never auto-acts).

Closes the gap vs MyVisaJobs/Levels.fyi/Boundless visa timeline planners
locked in closed UIs. Emits processing-coverage bands —
never auto-acts and never performs network I/O.

Distinct from ``VisaSponsorshipSignalExtractor`` and
``NoticePeriodConflictFlagger``. Optional later polish via GPT-5.5 /
Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class VisaTimelineGapReport:
    """Human-reviewable visa timeline report."""

    days_to_start: float
    estimated_processing_days: float
    buffer_days: float
    coverage_ratio: float
    remaining_cap: float
    coverage_band: str
    guidance: list[str]
    requires_human_review: bool
    auto_enroll: bool


class VisaTimelineGapAdvisor:
    """Advise visa timeline coverage bands for HITL review."""

    def advise(
        self,
        *,
        days_to_start: float,
        estimated_processing_days: float,
        buffer_days: float = 14.0,
    ) -> VisaTimelineGapReport:
        """Compute timeline coverage band.

        Args:
            days_to_start: Calendar days until preferred start (``> 0``).
            estimated_processing_days: Estimated visa processing days (``> 0``).
            buffer_days: Extra cushion days (``>= 0``).

        Returns:
            VisaTimelineGapReport with ``auto_enroll=False``.

        Raises:
            ValueError: On invalid numeric inputs.
        """

        if days_to_start <= 0:
            raise ValueError("days_to_start must be > 0")
        if estimated_processing_days <= 0:
            raise ValueError("estimated_processing_days must be > 0")
        if buffer_days < 0:
            raise ValueError("buffer_days must be >= 0")

        needed = estimated_processing_days + buffer_days
        coverage_ratio = round(min(days_to_start, needed) / needed, 4)
        remaining_cap = round(max(days_to_start - needed, 0.0), 2)

        if coverage_ratio >= 0.9:
            band = "well_covered"
        elif coverage_ratio >= 0.5:
            band = "partial_gap"
        else:
            band = "under_covered"

        guidance = [
            "Timeline math is advisory; verify consulate and counsel guidance.",
            "Do not auto-act from this advisor.",
        ]
        if band == "well_covered":
            guidance.append("Start date likely leaves room for processing + buffer.")
        elif band == "partial_gap":
            guidance.append("Partial gap; negotiate later start or premium processing.")
        else:
            guidance.append("Timeline thin vs processing; delay start or change visa path.")

        return VisaTimelineGapReport(
            days_to_start=float(days_to_start),
            estimated_processing_days=float(estimated_processing_days),
            buffer_days=float(buffer_days),
            coverage_ratio=float(coverage_ratio),
            remaining_cap=float(remaining_cap),
            coverage_band=band,
            guidance=guidance,
            requires_human_review=True,
            auto_enroll=False,
        )

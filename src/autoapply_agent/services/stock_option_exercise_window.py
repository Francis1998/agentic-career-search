"""HITL StockOptionExerciseWindowAdvisor (offline; never auto-acts).

Closes closed-UI planner gaps with coverage bands.
Never auto-acts and never performs network I/O.
Distinct from `IsoAmtExposureAdvisor` and `EquityVestingCliffAdvisor`.
Optional later polish via frontier LLMs must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class StockOptionExerciseWindowReport:
    """Human-reviewable report."""

    days_remaining: float
    min_exercise_days: float
    coverage_ratio: float
    remaining_cap: float
    coverage_band: str
    guidance: list[str]
    requires_human_review: bool
    auto_enroll: bool


class StockOptionExerciseWindowAdvisor:
    """Advise coverage bands for HITL review."""

    def advise(
        self,
        *,
        days_remaining: float,
        min_exercise_days: float,
    ) -> StockOptionExerciseWindowReport:
        """Compute coverage band.

        Args:
            days_remaining: Observed available quantity (``> 0``).
            min_exercise_days: Required quantity (``> 0``).

        Returns:
            StockOptionExerciseWindowReport with ``auto_enroll=False``.

        Raises:
            ValueError: On invalid numeric inputs.
        """

        if days_remaining <= 0:
            raise ValueError("days_remaining must be > 0")
        if min_exercise_days <= 0:
            raise ValueError("min_exercise_days must be > 0")

        coverage_ratio = round(
            min(days_remaining, min_exercise_days) / min_exercise_days,
            4,
        )
        remaining_cap = round(max(days_remaining - min_exercise_days, 0.0), 2)

        if coverage_ratio >= 0.9:
            band = "well_covered"
        elif coverage_ratio >= 0.5:
            band = "partial_gap"
        else:
            band = "under_covered"

        guidance = [
            "Advisory math only; verify against primary sources.",
            "Do not auto-act from this advisor.",
        ]
        if band == "well_covered":
            guidance.append("Coverage looks adequate for HITL confirmation.")
        elif band == "partial_gap":
            guidance.append("Partial gap; renegotiate or top-up before accepting.")
        else:
            guidance.append("Under-covered; escalate for human decision.")

        return StockOptionExerciseWindowReport(
            days_remaining=float(days_remaining),
            min_exercise_days=float(min_exercise_days),
            coverage_ratio=float(coverage_ratio),
            remaining_cap=float(remaining_cap),
            coverage_band=band,
            guidance=guidance,
            requires_human_review=True,
            auto_enroll=False,
        )

"""HITL NoticePeriodBuyoutGapAdvisor (offline; never auto-acts).

Closes closed-UI planner gaps with coverage bands.
Never auto-acts and never performs network I/O.
Distinct from `GardenLeaveGapAdvisor` and `SeverancePackageGapAdvisor`.
Optional later polish via frontier LLMs must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class NoticePeriodBuyoutGapReport:
    """Human-reviewable report."""

    buyout_weeks: float
    needed_weeks: float
    coverage_ratio: float
    remaining_cap: float
    coverage_band: str
    guidance: list[str]
    requires_human_review: bool
    auto_enroll: bool


class NoticePeriodBuyoutGapAdvisor:
    """Advise coverage bands for HITL review."""

    def advise(
        self,
        *,
        buyout_weeks: float,
        needed_weeks: float,
    ) -> NoticePeriodBuyoutGapReport:
        """Compute coverage band.

        Args:
            buyout_weeks: Observed value (>= 0).
            needed_weeks: Target value (> 0).

        Returns:
            NoticePeriodBuyoutGapReport with auto_enroll=False.

        Raises:
            ValueError: On invalid numeric inputs.
        """

        if buyout_weeks < 0:
            raise ValueError("buyout_weeks must be >= 0")
        if needed_weeks <= 0:
            raise ValueError("needed_weeks must be > 0")

        coverage_ratio = round(min(buyout_weeks, needed_weeks) / needed_weeks, 4)
        remaining_cap = round(max(needed_weeks - buyout_weeks, 0.0), 2)

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
            guidance.append("Partial gap; renegotiate terms carefully.")
        else:
            guidance.append("Under-covered; escalate for human decision.")

        return NoticePeriodBuyoutGapReport(
            buyout_weeks=float(buyout_weeks),
            needed_weeks=float(needed_weeks),
            coverage_ratio=float(coverage_ratio),
            remaining_cap=float(remaining_cap),
            coverage_band=band,
            guidance=guidance,
            requires_human_review=True,
            auto_enroll=False,
        )

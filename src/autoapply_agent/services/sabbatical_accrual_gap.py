"""HITL SabbaticalAccrualGapAdvisor (offline; never auto-acts).

Closes closed-UI planner gaps with coverage bands.
Never auto-acts and never performs network I/O.
Distinct from `SabbaticalEligibilityAdvisor` / `PtoCarryoverCapGapAdvisor`.
Gap vs Lattice/Workday/BambooHR sabbatical accrual planners.
Optional later polish via frontier LLMs must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class SabbaticalAccrualGapReport:
    """Human-reviewable report."""

    offered_months: float
    needed_months: float
    coverage_ratio: float
    remaining_cap: float
    coverage_band: str
    guidance: list[str]
    requires_human_review: bool
    auto_approve: bool


class SabbaticalAccrualGapAdvisor:
    """Advise coverage bands for HITL review."""

    def advise(
        self,
        *,
        offered_months: float,
        needed_months: float,
    ) -> SabbaticalAccrualGapReport:
        """Compute coverage band.

        Args:
            offered_months: Observed value (>= 0).
            needed_months: Target value (> 0).

        Returns:
            SabbaticalAccrualGapReport with auto_approve=False.

        Raises:
            ValueError: On invalid numeric inputs.
        """

        if offered_months < 0:
            raise ValueError("offered_months must be >= 0")
        if needed_months <= 0:
            raise ValueError("needed_months must be > 0")

        coverage_ratio = round(min(offered_months, needed_months) / needed_months, 4)
        remaining_cap = round(max(needed_months - offered_months, 0.0), 2)

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

        return SabbaticalAccrualGapReport(
            offered_months=float(offered_months),
            needed_months=float(needed_months),
            coverage_ratio=float(coverage_ratio),
            remaining_cap=float(remaining_cap),
            coverage_band=band,
            guidance=guidance,
            requires_human_review=True,
            auto_approve=False,
        )

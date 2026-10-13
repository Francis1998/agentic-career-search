"""HITL IpoLockupReleaseGapAdvisor (offline; never auto-acts).

Closes closed-UI planner gaps with coverage bands.
Never auto-acts and never performs network I/O.
Distinct from `EquityBlackoutWindowAdvisor` / `StockOptionExerciseWindowAdvisor`.
Optional later polish via frontier LLMs must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class IpoLockupReleaseGapReport:
    """Human-reviewable report."""

    days_to_lockup_end: float
    needed_liquidity_days: float
    coverage_ratio: float
    remaining_cap: float
    coverage_band: str
    guidance: list[str]
    requires_human_review: bool
    auto_enroll: bool


class IpoLockupReleaseGapAdvisor:
    """Advise coverage bands for HITL review."""

    def advise(
        self,
        *,
        days_to_lockup_end: float,
        needed_liquidity_days: float,
    ) -> IpoLockupReleaseGapReport:
        """Compute coverage band.

        Args:
            days_to_lockup_end: Observed value (>= 0).
            needed_liquidity_days: Target value (> 0).

        Returns:
            IpoLockupReleaseGapReport with auto_enroll=False.

        Raises:
            ValueError: On invalid numeric inputs.
        """

        if days_to_lockup_end < 0:
            raise ValueError("days_to_lockup_end must be >= 0")
        if needed_liquidity_days <= 0:
            raise ValueError("needed_liquidity_days must be > 0")

        coverage_ratio = round(
            min(days_to_lockup_end, needed_liquidity_days) / needed_liquidity_days, 4
        )
        remaining_cap = round(max(needed_liquidity_days - days_to_lockup_end, 0.0), 2)

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

        return IpoLockupReleaseGapReport(
            days_to_lockup_end=float(days_to_lockup_end),
            needed_liquidity_days=float(needed_liquidity_days),
            coverage_ratio=float(coverage_ratio),
            remaining_cap=float(remaining_cap),
            coverage_band=band,
            guidance=guidance,
            requires_human_review=True,
            auto_enroll=False,
        )

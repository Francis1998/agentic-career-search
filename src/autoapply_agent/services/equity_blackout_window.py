"""HITL EquityBlackoutWindowAdvisor (offline; never auto-acts).

Closes closed-UI planner gaps with coverage bands.
Never auto-acts and never performs network I/O.
Distinct from `StockOptionExerciseWindowAdvisor` and `RsuRefreshCadenceAdvisor`.
Optional later polish via frontier LLMs must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class EquityBlackoutWindowReport:
    """Human-reviewable report."""

    blackout_days_remaining: float
    planned_liquidity_days: float
    coverage_ratio: float
    remaining_cap: float
    coverage_band: str
    guidance: list[str]
    requires_human_review: bool
    auto_enroll: bool


class EquityBlackoutWindowAdvisor:
    """Advise coverage bands for HITL review."""

    def advise(
        self,
        *,
        blackout_days_remaining: float,
        planned_liquidity_days: float,
    ) -> EquityBlackoutWindowReport:
        """Compute coverage band.

        Args:
            blackout_days_remaining: Observed metric (``> 0``).
            planned_liquidity_days: Target value (``> 0``).

        Returns:
            EquityBlackoutWindowReport with ``auto_enroll=False``.

        Raises:
            ValueError: On invalid numeric inputs.
        """

        if blackout_days_remaining <= 0:
            raise ValueError("blackout_days_remaining must be > 0")
        if planned_liquidity_days <= 0:
            raise ValueError("planned_liquidity_days must be > 0")

        coverage_ratio = round(
            min(blackout_days_remaining, planned_liquidity_days) / planned_liquidity_days,
            4,
        )
        remaining_cap = round(max(blackout_days_remaining - planned_liquidity_days, 0.0), 2)

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

        return EquityBlackoutWindowReport(
            blackout_days_remaining=float(blackout_days_remaining),
            planned_liquidity_days=float(planned_liquidity_days),
            coverage_ratio=float(coverage_ratio),
            remaining_cap=float(remaining_cap),
            coverage_band=band,
            guidance=guidance,
            requires_human_review=True,
            auto_enroll=False,
        )

"""HITL UnlimitedPtoUtilizationGapAdvisor (offline; never auto-acts).

Closes closed-UI planner gaps with coverage bands.
Never auto-acts and never performs network I/O.
Distinct from `PtoAccrualCliffAdvisor` / `PtoCarryoverCapGapAdvisor`.
Optional later polish via frontier LLMs must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class UnlimitedPtoUtilizationGapReport:
    """Human-reviewable report."""

    days_taken: float
    peer_median_days: float
    coverage_ratio: float
    remaining_cap: float
    coverage_band: str
    guidance: list[str]
    requires_human_review: bool
    auto_enroll: bool


class UnlimitedPtoUtilizationGapAdvisor:
    """Advise coverage bands for HITL review."""

    def advise(
        self,
        *,
        days_taken: float,
        peer_median_days: float,
    ) -> UnlimitedPtoUtilizationGapReport:
        """Compute coverage band.

        Args:
            days_taken: Observed value (>= 0).
            peer_median_days: Target value (> 0).

        Returns:
            UnlimitedPtoUtilizationGapReport with auto_enroll=False.

        Raises:
            ValueError: On invalid numeric inputs.
        """

        if days_taken < 0:
            raise ValueError("days_taken must be >= 0")
        if peer_median_days <= 0:
            raise ValueError("peer_median_days must be > 0")

        coverage_ratio = round(min(days_taken, peer_median_days) / peer_median_days, 4)
        remaining_cap = round(max(peer_median_days - days_taken, 0.0), 2)

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

        return UnlimitedPtoUtilizationGapReport(
            days_taken=float(days_taken),
            peer_median_days=float(peer_median_days),
            coverage_ratio=float(coverage_ratio),
            remaining_cap=float(remaining_cap),
            coverage_band=band,
            guidance=guidance,
            requires_human_review=True,
            auto_enroll=False,
        )

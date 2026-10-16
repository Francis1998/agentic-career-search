"""HITL SummerFridayGapAdvisor (offline; never auto-acts).

Closes closed-UI planner gaps with coverage bands.
Never auto-acts and never performs network I/O.
Distinct from `UnlimitedPtoUtilizationGapAdvisor` / `PtoCarryoverCapGapAdvisor`.
Optional later polish via frontier LLMs must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class SummerFridayGapReport:
    """Human-reviewable report."""

    offered_fridays: float
    peer_median_fridays: float
    coverage_ratio: float
    remaining_cap: float
    coverage_band: str
    guidance: list[str]
    requires_human_review: bool
    auto_enroll: bool


class SummerFridayGapAdvisor:
    """Advise coverage bands for HITL review."""

    def advise(
        self,
        *,
        offered_fridays: float,
        peer_median_fridays: float,
    ) -> SummerFridayGapReport:
        """Compute coverage band.

        Args:
            offered_fridays: Observed value (>= 0).
            peer_median_fridays: Target value (> 0).

        Returns:
            SummerFridayGapReport with auto_enroll=False.

        Raises:
            ValueError: On invalid numeric inputs.
        """

        if offered_fridays < 0:
            raise ValueError("offered_fridays must be >= 0")
        if peer_median_fridays <= 0:
            raise ValueError("peer_median_fridays must be > 0")

        coverage_ratio = round(min(offered_fridays, peer_median_fridays) / peer_median_fridays, 4)
        remaining_cap = round(max(peer_median_fridays - offered_fridays, 0.0), 2)

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

        return SummerFridayGapReport(
            offered_fridays=float(offered_fridays),
            peer_median_fridays=float(peer_median_fridays),
            coverage_ratio=float(coverage_ratio),
            remaining_cap=float(remaining_cap),
            coverage_band=band,
            guidance=guidance,
            requires_human_review=True,
            auto_enroll=False,
        )

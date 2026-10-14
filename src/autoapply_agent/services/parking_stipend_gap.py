"""HITL ParkingStipendGapAdvisor (offline; never auto-acts).

Closes closed-UI planner gaps with coverage bands.
Never auto-acts and never performs network I/O.
Distinct from `TransitCommuteBenefitGapAdvisor` / `CommuteCostTradeoffAdvisor`.
Optional later polish via frontier LLMs must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class ParkingStipendGapReport:
    """Human-reviewable report."""

    offered_parking_usd: float
    needed_parking_usd: float
    coverage_ratio: float
    remaining_cap: float
    coverage_band: str
    guidance: list[str]
    requires_human_review: bool
    auto_enroll: bool


class ParkingStipendGapAdvisor:
    """Advise coverage bands for HITL review."""

    def advise(
        self,
        *,
        offered_parking_usd: float,
        needed_parking_usd: float,
    ) -> ParkingStipendGapReport:
        """Compute coverage band.

        Args:
            offered_parking_usd: Observed value (>= 0).
            needed_parking_usd: Target value (> 0).

        Returns:
            ParkingStipendGapReport with auto_enroll=False.

        Raises:
            ValueError: On invalid numeric inputs.
        """

        if offered_parking_usd < 0:
            raise ValueError("offered_parking_usd must be >= 0")
        if needed_parking_usd <= 0:
            raise ValueError("needed_parking_usd must be > 0")

        coverage_ratio = round(min(offered_parking_usd, needed_parking_usd) / needed_parking_usd, 4)
        remaining_cap = round(max(needed_parking_usd - offered_parking_usd, 0.0), 2)

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

        return ParkingStipendGapReport(
            offered_parking_usd=float(offered_parking_usd),
            needed_parking_usd=float(needed_parking_usd),
            coverage_ratio=float(coverage_ratio),
            remaining_cap=float(remaining_cap),
            coverage_band=band,
            guidance=guidance,
            requires_human_review=True,
            auto_enroll=False,
        )

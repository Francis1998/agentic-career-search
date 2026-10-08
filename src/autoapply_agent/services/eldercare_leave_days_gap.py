"""HITL EldercareLeaveDaysGapAdvisor (offline; never auto-acts).

Closes closed-UI planner gaps with coverage bands.
Never auto-acts and never performs network I/O.
Distinct from `ParentalLeaveGapAdvisor` and `PaidFamilyLeaveStateGapAdvisor`.
Optional later polish via frontier LLMs must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class EldercareLeaveDaysGapReport:
    """Human-reviewable report."""

    offered_days: float
    needed_days: float
    coverage_ratio: float
    remaining_cap: float
    coverage_band: str
    guidance: list[str]
    requires_human_review: bool
    auto_enroll: bool


class EldercareLeaveDaysGapAdvisor:
    """Advise coverage bands for HITL review."""

    def advise(
        self,
        *,
        offered_days: float,
        needed_days: float,
    ) -> EldercareLeaveDaysGapReport:
        """Compute coverage band.

        Args:
            offered_days: Observed metric (``> 0``).
            needed_days: Target value (``> 0``).

        Returns:
            EldercareLeaveDaysGapReport with ``auto_enroll=False``.

        Raises:
            ValueError: On invalid numeric inputs.
        """

        if offered_days <= 0:
            raise ValueError("offered_days must be > 0")
        if needed_days <= 0:
            raise ValueError("needed_days must be > 0")

        coverage_ratio = round(
            min(offered_days, needed_days) / needed_days,
            4,
        )
        remaining_cap = round(max(offered_days - needed_days, 0.0), 2)

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

        return EldercareLeaveDaysGapReport(
            offered_days=float(offered_days),
            needed_days=float(needed_days),
            coverage_ratio=float(coverage_ratio),
            remaining_cap=float(remaining_cap),
            coverage_band=band,
            guidance=guidance,
            requires_human_review=True,
            auto_enroll=False,
        )

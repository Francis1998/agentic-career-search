"""HITL CommuteTimeValueAdvisor (offline; never auto-acts).

Closes closed-UI planner gaps with coverage bands.
Never auto-acts and never performs network I/O.
Distinct from `CommuteCostTradeoffAdvisor` and `TransitCommuteBenefitGapAdvisor`.
Optional later polish via frontier LLMs must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class CommuteTimeValueReport:
    """Human-reviewable report."""

    weekly_commute_hours: float
    hourly_opportunity_cost: float
    weekly_time_value: float
    soft_limit: float
    hard_limit: float
    coverage_band: str
    guidance: list[str]
    requires_human_review: bool
    auto_enroll: bool


class CommuteTimeValueAdvisor:
    """Advise commute time-value bands for HITL review."""

    def advise(
        self,
        *,
        weekly_commute_hours: float,
        hourly_opportunity_cost: float,
        soft_limit: float = 200.0,
        hard_limit: float = 500.0,
    ) -> CommuteTimeValueReport:
        """Compute time-value band.

        Args:
            weekly_commute_hours: Weekly commute hours (``> 0``).
            hourly_opportunity_cost: $/hour opportunity cost (``> 0``).
            soft_limit: Soft weekly time-value budget (``> 0``).
            hard_limit: Hard weekly time-value budget (``> soft_limit``).

        Returns:
            CommuteTimeValueReport with ``auto_enroll=False``.

        Raises:
            ValueError: On invalid numeric inputs.
        """

        if weekly_commute_hours <= 0:
            raise ValueError("weekly_commute_hours must be > 0")
        if hourly_opportunity_cost <= 0:
            raise ValueError("hourly_opportunity_cost must be > 0")
        if soft_limit <= 0:
            raise ValueError("soft_limit must be > 0")
        if hard_limit <= soft_limit:
            raise ValueError("hard_limit must be > soft_limit")

        weekly_time_value = round(weekly_commute_hours * hourly_opportunity_cost, 2)

        if weekly_time_value <= soft_limit:
            band = "well_covered"
        elif weekly_time_value <= hard_limit:
            band = "partial_gap"
        else:
            band = "under_covered"

        guidance = [
            "Advisory math only; verify against primary sources.",
            "Do not auto-act from this advisor.",
        ]
        if band == "well_covered":
            guidance.append("Commute time-value looks acceptable for HITL confirmation.")
        elif band == "partial_gap":
            guidance.append("Elevated commute time-value; renegotiate remote/hybrid days.")
        else:
            guidance.append("Commute time-value exceeds hard budget; escalate for human decision.")

        return CommuteTimeValueReport(
            weekly_commute_hours=float(weekly_commute_hours),
            hourly_opportunity_cost=float(hourly_opportunity_cost),
            weekly_time_value=float(weekly_time_value),
            soft_limit=float(soft_limit),
            hard_limit=float(hard_limit),
            coverage_band=band,
            guidance=guidance,
            requires_human_review=True,
            auto_enroll=False,
        )

"""HITL bereavement leave gap advisor (offline; never auto-approves).

Closes the gap vs Lattice / Workday / Levels.fyi bereavement-leave planners
locked in closed UIs. Given offered bereavement days and needed days,
emits coverage bands — never auto-approves leave and never performs
network I/O.

Distinct from ``ParentalLeaveGapAdvisor`` (parental weeks) and
``SabbaticalEligibilityAdvisor`` (sabbatical). Optional later polish via
GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class BereavementLeaveGapReport:
    """Human-reviewable bereavement leave coverage report."""

    offered_days: float
    needed_days: float
    coverage_ratio: float
    coverage_band: str
    guidance: list[str]
    requires_human_review: bool
    auto_approve: bool


class BereavementLeaveGapAdvisor:
    """Advise bereavement leave coverage vs needed days."""

    def advise(
        self,
        *,
        offered_days: float,
        needed_days: float,
    ) -> BereavementLeaveGapReport:
        """Compute bereavement leave coverage band.

        Args:
            offered_days: Employer-offered bereavement days (``> 0``).
            needed_days: Days the worker needs (``> 0``).

        Returns:
            BereavementLeaveGapReport with ``auto_approve=False``.

        Raises:
            ValueError: On invalid numeric inputs.
        """

        if offered_days <= 0:
            raise ValueError("offered_days must be > 0")
        if needed_days <= 0:
            raise ValueError("needed_days must be > 0")

        coverage_ratio = round(offered_days / needed_days, 4)

        if coverage_ratio >= 1.0:
            band = "well_covered"
        elif coverage_ratio >= 0.5:
            band = "partial_gap"
        else:
            band = "under_covered"

        guidance = [
            "Bereavement leave math is advisory; verify relationship tiers and travel exceptions.",
            "Do not auto-approve bereavement leave from this advisor.",
        ]
        if band == "well_covered":
            guidance.append(
                "Offered days cover need; confirm manager notification and documentation rules."
            )
        elif band == "partial_gap":
            guidance.append("Partial coverage; plan PTO/unpaid bridge for remaining days.")
        else:
            guidance.append("Policy thin vs need; request exception or unpaid leave bridge.")

        return BereavementLeaveGapReport(
            offered_days=float(offered_days),
            needed_days=float(needed_days),
            coverage_ratio=float(coverage_ratio),
            coverage_band=band,
            guidance=guidance,
            requires_human_review=True,
            auto_approve=False,
        )

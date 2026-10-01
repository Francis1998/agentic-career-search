"""HITL TransitCommuteBenefitGapAdvisor (offline; never auto-acts).

Closes the gap vs WageWorks/CommuterBenefits/TransitChek/Levels.fyi
transit-benefit planners locked in closed UIs. Emits coverage bands —
never auto-acts and never performs network I/O.

Distinct from ``CommuteCostTradeoffAdvisor`` and
``HomeOfficeStipendGapAdvisor``. Optional later polish via GPT-5.5 /
Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class TransitCommuteBenefitGapReport:
    """Human-reviewable coverage report."""

    monthly_transit_need_usd: float
    employer_transit_benefit_usd: float
    planned_claim_usd: float
    coverage_ratio: float
    remaining_cap_usd: float
    coverage_band: str
    guidance: list[str]
    requires_human_review: bool
    auto_claim: bool


class TransitCommuteBenefitGapAdvisor:
    """Advise coverage bands for HITL review."""

    def advise(
        self,
        *,
        monthly_transit_need_usd: float,
        employer_transit_benefit_usd: float,
        planned_claim_usd: float,
    ) -> TransitCommuteBenefitGapReport:
        """Compute coverage band.

        Args:
            monthly_transit_need_usd: Monthly transit need (``> 0``).
            employer_transit_benefit_usd: Employer monthly transit benefit (``> 0``).
            planned_claim_usd: Planned monthly claim (``>= 0``).

        Returns:
            TransitCommuteBenefitGapReport with ``auto_claim=False``.

        Raises:
            ValueError: On invalid numeric inputs.
        """

        if monthly_transit_need_usd <= 0:
            raise ValueError("monthly_transit_need_usd must be > 0")
        if employer_transit_benefit_usd <= 0:
            raise ValueError("employer_transit_benefit_usd must be > 0")
        if planned_claim_usd < 0:
            raise ValueError("planned_claim_usd must be >= 0")

        covered = min(employer_transit_benefit_usd, planned_claim_usd)
        coverage_ratio = round(covered / monthly_transit_need_usd, 4)
        remaining_cap = round(max(employer_transit_benefit_usd - planned_claim_usd, 0.0), 2)

        if coverage_ratio >= 0.9:
            band = "well_covered"
        elif coverage_ratio >= 0.5:
            band = "partial_gap"
        else:
            band = "under_covered"

        guidance = [
            "Transit-benefit math is advisory; verify pre-tax vs taxable stipend rules.",
            "Do not auto-enroll transit benefits from this advisor.",
        ]
        if band == "well_covered":
            guidance.append("Benefit covers most transit need; confirm parking stacking.")
        elif band == "partial_gap":
            guidance.append("Partial transit gap; budget out-of-pocket for peak months.")
        else:
            guidance.append("Benefit thin vs transit need; negotiate stipend or hybrid.")

        return TransitCommuteBenefitGapReport(
            monthly_transit_need_usd=float(monthly_transit_need_usd),
            employer_transit_benefit_usd=float(employer_transit_benefit_usd),
            planned_claim_usd=float(planned_claim_usd),
            coverage_ratio=float(coverage_ratio),
            remaining_cap_usd=float(remaining_cap),
            coverage_band=band,
            guidance=guidance,
            requires_human_review=True,
            auto_claim=False,
        )

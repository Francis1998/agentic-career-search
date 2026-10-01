"""HITL AdoptionAssistanceGapAdvisor (offline; never auto-acts).

Closes the gap vs Carrot/Progyny/Maven/Levels.fyi adoption-assistance
planners locked in closed UIs. Emits coverage bands — never auto-acts
and never performs network I/O.

Distinct from ``FertilityBenefitGapAdvisor`` and
``ParentalLeaveGapAdvisor``. Optional later polish via GPT-5.5 /
Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class AdoptionAssistanceGapReport:
    """Human-reviewable coverage report."""

    adoption_cost_budget_usd: float
    employer_assistance_usd: float
    planned_claim_usd: float
    coverage_ratio: float
    remaining_cap_usd: float
    coverage_band: str
    guidance: list[str]
    requires_human_review: bool
    auto_claim: bool


class AdoptionAssistanceGapAdvisor:
    """Advise coverage bands for HITL review."""

    def advise(
        self,
        *,
        adoption_cost_budget_usd: float,
        employer_assistance_usd: float,
        planned_claim_usd: float,
    ) -> AdoptionAssistanceGapReport:
        """Compute coverage band.

        Args:
            adoption_cost_budget_usd: Household adoption cost budget (``> 0``).
            employer_assistance_usd: Employer adoption assistance value (``> 0``).
            planned_claim_usd: Planned claim against assistance (``>= 0``).

        Returns:
            AdoptionAssistanceGapReport with ``auto_claim=False``.

        Raises:
            ValueError: On invalid numeric inputs.
        """

        if adoption_cost_budget_usd <= 0:
            raise ValueError("adoption_cost_budget_usd must be > 0")
        if employer_assistance_usd <= 0:
            raise ValueError("employer_assistance_usd must be > 0")
        if planned_claim_usd < 0:
            raise ValueError("planned_claim_usd must be >= 0")

        covered = min(employer_assistance_usd, planned_claim_usd)
        coverage_ratio = round(covered / adoption_cost_budget_usd, 4)
        remaining_cap = round(max(employer_assistance_usd - planned_claim_usd, 0.0), 2)

        if coverage_ratio >= 0.9:
            band = "well_covered"
        elif coverage_ratio >= 0.5:
            band = "partial_gap"
        else:
            band = "under_covered"

        guidance = [
            "Adoption-assistance math is advisory; verify agency vs legal fee rules.",
            "Do not auto-claim adoption assistance from this advisor.",
        ]
        if band == "well_covered":
            guidance.append("Assistance covers most adoption budget; confirm tax credits.")
        elif band == "partial_gap":
            guidance.append("Partial assistance gap; budget out-of-pocket for retainers.")
        else:
            guidance.append("Assistance thin vs budget; negotiate higher cap or FSA bridge.")

        return AdoptionAssistanceGapReport(
            adoption_cost_budget_usd=float(adoption_cost_budget_usd),
            employer_assistance_usd=float(employer_assistance_usd),
            planned_claim_usd=float(planned_claim_usd),
            coverage_ratio=float(coverage_ratio),
            remaining_cap_usd=float(remaining_cap),
            coverage_band=band,
            guidance=guidance,
            requires_human_review=True,
            auto_claim=False,
        )

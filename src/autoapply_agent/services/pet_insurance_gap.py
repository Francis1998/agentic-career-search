"""HITL pet insurance gap advisor (offline; never auto-claims).

Closes the gap vs Figo/Trupanion/Levels.fyi/Blind pet-insurance benefit planners
locked in closed UIs. Emits coverage bands — never auto-claims and never
performs network I/O.

Distinct from ``HomeOfficeStipendGapAdvisor`` and
``FertilityBenefitGapAdvisor``. Optional later polish via
GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class PetInsuranceGapReport:
    """Human-reviewable coverage report."""

    annual_vet_cost_usd: float
    employer_stipend_usd: float
    planned_claim_usd: float
    coverage_ratio: float
    remaining_cap_usd: float
    coverage_band: str
    guidance: list[str]
    requires_human_review: bool
    auto_claim: bool


class PetInsuranceGapAdvisor:
    """Advise coverage bands for HITL review."""

    def advise(
        self,
        *,
        annual_vet_cost_usd: float,
        employer_stipend_usd: float,
        planned_claim_usd: float,
    ) -> PetInsuranceGapReport:
        """Compute coverage band.

        Args:
            annual_vet_cost_usd: Expected annual veterinary cost (``> 0``).
            employer_stipend_usd: Employer annual pet insurance stipend (``> 0``).
            planned_claim_usd: Planned claim against the stipend (``>= 0``).

        Returns:
            PetInsuranceGapReport with ``auto_claim=False``.

        Raises:
            ValueError: On invalid numeric inputs.
        """

        if annual_vet_cost_usd <= 0:
            raise ValueError("annual_vet_cost_usd must be > 0")
        if employer_stipend_usd <= 0:
            raise ValueError("employer_stipend_usd must be > 0")
        if planned_claim_usd < 0:
            raise ValueError("planned_claim_usd must be >= 0")

        covered = min(employer_stipend_usd, planned_claim_usd)
        coverage_ratio = round(covered / annual_vet_cost_usd, 4)
        remaining_cap = round(max(employer_stipend_usd - planned_claim_usd, 0.0), 2)

        if coverage_ratio >= 0.9:
            band = "well_covered"
        elif coverage_ratio >= 0.5:
            band = "partial_gap"
        else:
            band = "under_covered"

        guidance = [
            "Pet insurance math is advisory; verify waiting periods and caps.",
            "Do not auto-claim pet insurance benefits from this advisor.",
        ]
        if band == "well_covered":
            guidance.append("Stipend covers most vet cost; confirm eligible pets.")
        elif band == "partial_gap":
            guidance.append("Partial coverage; budget out-of-pocket for chronic care.")
        else:
            guidance.append("Stipend thin vs vet cost; negotiate raise or HSA bridge.")

        return PetInsuranceGapReport(
            annual_vet_cost_usd=float(annual_vet_cost_usd),
            employer_stipend_usd=float(employer_stipend_usd),
            planned_claim_usd=float(planned_claim_usd),
            coverage_ratio=float(coverage_ratio),
            remaining_cap_usd=float(remaining_cap),
            coverage_band=band,
            guidance=guidance,
            requires_human_review=True,
            auto_claim=False,
        )

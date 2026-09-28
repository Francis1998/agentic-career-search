"""HITL fertility benefit gap advisor (offline; never auto-claims).

Closes the gap vs Levels.fyi / Blind / Carrot / Progyny fertility-benefit
planners locked in closed UIs. Given annual treatment cost, employer
fertility benefit cap, and planned claim USD, emits coverage bands —
never auto-claims and never performs network I/O.

Distinct from ``TuitionReimbursementGapAdvisor`` (tuition) and
``ParentalLeaveGapAdvisor`` (leave weeks). Optional later polish via
GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class FertilityBenefitGapReport:
    """Human-reviewable fertility benefit coverage report."""

    annual_treatment_usd: float
    employer_cap_usd: float
    planned_claim_usd: float
    coverage_ratio: float
    remaining_cap_usd: float
    coverage_band: str
    guidance: list[str]
    requires_human_review: bool
    auto_claim: bool


class FertilityBenefitGapAdvisor:
    """Advise fertility benefit coverage vs employer annual cap."""

    def advise(
        self,
        *,
        annual_treatment_usd: float,
        employer_cap_usd: float,
        planned_claim_usd: float,
    ) -> FertilityBenefitGapReport:
        """Compute fertility benefit coverage band.

        Args:
            annual_treatment_usd: Expected annual treatment cost (``> 0``).
            employer_cap_usd: Employer annual fertility benefit cap (``> 0``).
            planned_claim_usd: Planned claim against the cap (``>= 0``).

        Returns:
            FertilityBenefitGapReport with ``auto_claim=False``.

        Raises:
            ValueError: On invalid numeric inputs.
        """

        if annual_treatment_usd <= 0:
            raise ValueError("annual_treatment_usd must be > 0")
        if employer_cap_usd <= 0:
            raise ValueError("employer_cap_usd must be > 0")
        if planned_claim_usd < 0:
            raise ValueError("planned_claim_usd must be >= 0")

        coverage_ratio = round(min(employer_cap_usd, planned_claim_usd) / annual_treatment_usd, 4)
        remaining_cap = round(max(employer_cap_usd - planned_claim_usd, 0.0), 2)

        if coverage_ratio >= 0.9:
            band = "well_covered"
        elif coverage_ratio >= 0.5:
            band = "partial_gap"
        else:
            band = "under_covered"

        guidance = [
            "Fertility benefit math is advisory; verify lifetime caps, waitlists, and clinics.",
            "Do not auto-claim fertility benefits from this advisor.",
        ]
        if band == "well_covered":
            guidance.append("Cap covers most treatment cost; confirm pre-auth and cycle timing.")
        elif band == "partial_gap":
            guidance.append(
                "Partial coverage; budget out-of-pocket remainder before starting a cycle."
            )
        else:
            guidance.append("Cap thin vs treatment cost; negotiate lifetime cap or HSA/FSA bridge.")

        return FertilityBenefitGapReport(
            annual_treatment_usd=float(annual_treatment_usd),
            employer_cap_usd=float(employer_cap_usd),
            planned_claim_usd=float(planned_claim_usd),
            coverage_ratio=float(coverage_ratio),
            remaining_cap_usd=float(remaining_cap),
            coverage_band=band,
            guidance=guidance,
            requires_human_review=True,
            auto_claim=False,
        )

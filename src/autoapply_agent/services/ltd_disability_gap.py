"""HITL LtdDisabilityGapAdvisor (offline; never auto-acts).

Closes the gap vs Unum/MetLife/Guardian/Levels.fyi LTD planners locked in
closed UIs. Emits coverage bands — never auto-acts and never performs
network I/O.

Distinct from ``IdentityTheftProtectionGapAdvisor`` and
``LegalInsuranceGapAdvisor``. Optional later polish via GPT-5.5 /
Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class LtdDisabilityGapReport:
    """Human-reviewable coverage report."""

    income_replacement_need_usd: float
    employer_ltd_benefit_usd: float
    planned_claim_usd: float
    coverage_ratio: float
    remaining_cap_usd: float
    coverage_band: str
    guidance: list[str]
    requires_human_review: bool
    auto_claim: bool


class LtdDisabilityGapAdvisor:
    """Advise coverage bands for HITL review."""

    def advise(
        self,
        *,
        income_replacement_need_usd: float,
        employer_ltd_benefit_usd: float,
        planned_claim_usd: float,
    ) -> LtdDisabilityGapReport:
        """Compute coverage band.

        Args:
            income_replacement_need_usd: Needed annual income replacement (``> 0``).
            employer_ltd_benefit_usd: Employer LTD benefit annual value (``> 0``).
            planned_claim_usd: Planned claim against LTD (``>= 0``).

        Returns:
            LtdDisabilityGapReport with ``auto_claim=False``.

        Raises:
            ValueError: On invalid numeric inputs.
        """

        if income_replacement_need_usd <= 0:
            raise ValueError("income_replacement_need_usd must be > 0")
        if employer_ltd_benefit_usd <= 0:
            raise ValueError("employer_ltd_benefit_usd must be > 0")
        if planned_claim_usd < 0:
            raise ValueError("planned_claim_usd must be >= 0")

        covered = min(employer_ltd_benefit_usd, planned_claim_usd)
        coverage_ratio = round(covered / income_replacement_need_usd, 4)
        remaining_cap = round(max(employer_ltd_benefit_usd - planned_claim_usd, 0.0), 2)

        if coverage_ratio >= 0.9:
            band = "well_covered"
        elif coverage_ratio >= 0.5:
            band = "partial_gap"
        else:
            band = "under_covered"

        guidance = [
            "LTD math is advisory; verify elimination period and disability definition.",
            "Do not auto-enroll LTD coverage from this advisor.",
        ]
        if band == "well_covered":
            guidance.append("LTD covers most income need; confirm own-occupation riders.")
        elif band == "partial_gap":
            guidance.append("Partial LTD gap; budget private LTD bridge or HSA buffer.")
        else:
            guidance.append("LTD thin vs income need; negotiate higher % or private policy.")

        return LtdDisabilityGapReport(
            income_replacement_need_usd=float(income_replacement_need_usd),
            employer_ltd_benefit_usd=float(employer_ltd_benefit_usd),
            planned_claim_usd=float(planned_claim_usd),
            coverage_ratio=float(coverage_ratio),
            remaining_cap_usd=float(remaining_cap),
            coverage_band=band,
            guidance=guidance,
            requires_human_review=True,
            auto_claim=False,
        )

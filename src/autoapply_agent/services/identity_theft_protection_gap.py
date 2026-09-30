"""HITL IdentityTheftProtectionGapAdvisor (offline; never auto-acts).

Closes the gap vs Norton/LifeLock/Aura/Levels.fyi identity-theft benefit planners
locked in closed UIs. Emits coverage bands — never auto-acts and never
performs network I/O.

Distinct from ``WellnessStipendGapAdvisor`` and
``PetInsuranceGapAdvisor``. Optional later polish via
GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class IdentityTheftProtectionGapReport:
    """Human-reviewable coverage report."""

    household_risk_budget_usd: float
    employer_benefit_usd: float
    planned_claim_usd: float
    coverage_ratio: float
    remaining_cap_usd: float
    coverage_band: str
    guidance: list[str]
    requires_human_review: bool
    auto_claim: bool


class IdentityTheftProtectionGapAdvisor:
    """Advise coverage bands for HITL review."""

    def advise(
        self,
        *,
        household_risk_budget_usd: float,
        employer_benefit_usd: float,
        planned_claim_usd: float,
    ) -> IdentityTheftProtectionGapReport:
        """Compute coverage band.

        Args:
            household_risk_budget_usd: Household identity-risk budget (``> 0``).
            employer_benefit_usd: Employer identity-theft benefit value (``> 0``).
            planned_claim_usd: Planned claim against the benefit (``>= 0``).

        Returns:
            IdentityTheftProtectionGapReport with ``auto_claim=False``.

        Raises:
            ValueError: On invalid numeric inputs.
        """

        if household_risk_budget_usd <= 0:
            raise ValueError("household_risk_budget_usd must be > 0")
        if employer_benefit_usd <= 0:
            raise ValueError("employer_benefit_usd must be > 0")
        if planned_claim_usd < 0:
            raise ValueError("planned_claim_usd must be >= 0")

        covered = min(employer_benefit_usd, planned_claim_usd)
        coverage_ratio = round(covered / household_risk_budget_usd, 4)
        remaining_cap = round(max(employer_benefit_usd - planned_claim_usd, 0.0), 2)

        if coverage_ratio >= 0.9:
            band = "well_covered"
        elif coverage_ratio >= 0.5:
            band = "partial_gap"
        else:
            band = "under_covered"

        guidance = [
            "Identity-theft benefit math is advisory; verify restoration caps.",
            "Do not auto-enroll identity protection from this advisor.",
        ]
        if band == "well_covered":
            guidance.append("Benefit covers most risk budget; confirm family seats.")
        elif band == "partial_gap":
            guidance.append("Partial coverage; budget out-of-pocket for restoration riders.")
        else:
            guidance.append("Benefit thin vs risk budget; negotiate higher tier or HSA bridge.")

        return IdentityTheftProtectionGapReport(
            household_risk_budget_usd=float(household_risk_budget_usd),
            employer_benefit_usd=float(employer_benefit_usd),
            planned_claim_usd=float(planned_claim_usd),
            coverage_ratio=float(coverage_ratio),
            remaining_cap_usd=float(remaining_cap),
            coverage_band=band,
            guidance=guidance,
            requires_human_review=True,
            auto_claim=False,
        )

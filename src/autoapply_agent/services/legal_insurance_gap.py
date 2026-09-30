"""HITL LegalInsuranceGapAdvisor (offline; never auto-acts).

Closes the gap vs LegalShield/ARAG/Levels.fyi/Blind legal-plan planners
locked in closed UIs. Emits coverage bands — never auto-acts and never
performs network I/O.

Distinct from ``PetInsuranceGapAdvisor`` and
``DependentCareFsaGapAdvisor``. Optional later polish via
GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class LegalInsuranceGapReport:
    """Human-reviewable coverage report."""

    annual_legal_need_usd: float
    employer_plan_value_usd: float
    planned_use_usd: float
    coverage_ratio: float
    remaining_cap_usd: float
    coverage_band: str
    guidance: list[str]
    requires_human_review: bool
    auto_claim: bool


class LegalInsuranceGapAdvisor:
    """Advise coverage bands for HITL review."""

    def advise(
        self,
        *,
        annual_legal_need_usd: float,
        employer_plan_value_usd: float,
        planned_use_usd: float,
    ) -> LegalInsuranceGapReport:
        """Compute coverage band.

        Args:
            annual_legal_need_usd: Expected annual legal-service need (``> 0``).
            employer_plan_value_usd: Employer legal-plan annual value (``> 0``).
            planned_use_usd: Planned use against the plan (``>= 0``).

        Returns:
            LegalInsuranceGapReport with ``auto_claim=False``.

        Raises:
            ValueError: On invalid numeric inputs.
        """

        if annual_legal_need_usd <= 0:
            raise ValueError("annual_legal_need_usd must be > 0")
        if employer_plan_value_usd <= 0:
            raise ValueError("employer_plan_value_usd must be > 0")
        if planned_use_usd < 0:
            raise ValueError("planned_use_usd must be >= 0")

        covered = min(employer_plan_value_usd, planned_use_usd)
        coverage_ratio = round(covered / annual_legal_need_usd, 4)
        remaining_cap = round(max(employer_plan_value_usd - planned_use_usd, 0.0), 2)

        if coverage_ratio >= 0.9:
            band = "well_covered"
        elif coverage_ratio >= 0.5:
            band = "partial_gap"
        else:
            band = "under_covered"

        guidance = [
            "Legal plan math is advisory; verify covered matters and caps.",
            "Do not auto-enroll legal insurance from this advisor.",
        ]
        if band == "well_covered":
            guidance.append("Plan covers most legal need; confirm covered matter types.")
        elif band == "partial_gap":
            guidance.append("Partial coverage; budget out-of-pocket for uncovered matters.")
        else:
            guidance.append("Plan thin vs legal need; negotiate raise or supplemental plan.")

        return LegalInsuranceGapReport(
            annual_legal_need_usd=float(annual_legal_need_usd),
            employer_plan_value_usd=float(employer_plan_value_usd),
            planned_use_usd=float(planned_use_usd),
            coverage_ratio=float(coverage_ratio),
            remaining_cap_usd=float(remaining_cap),
            coverage_band=band,
            guidance=guidance,
            requires_human_review=True,
            auto_claim=False,
        )

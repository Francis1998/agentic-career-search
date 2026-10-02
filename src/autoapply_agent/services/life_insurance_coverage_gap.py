"""HITL LifeInsuranceCoverageGapAdvisor (offline; never auto-acts).

Closes the gap vs MetLife/Guardian/Prudential/Levels.fyi life-insurance planners
locked in closed UIs. Emits coverage bands —
never auto-acts and never performs network I/O.

Distinct from ``LtdDisabilityGapAdvisor`` and
``IdentityTheftProtectionGapAdvisor``. Optional later polish via GPT-5.5 /
Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class LifeInsuranceCoverageGapReport:
    """Human-reviewable coverage report."""

    annual_income_need_usd: float
    employer_life_cover_usd: float
    planned_cover_usd: float
    coverage_ratio: float
    remaining_cap: float
    coverage_band: str
    guidance: list[str]
    requires_human_review: bool
    auto_enroll: bool


class LifeInsuranceCoverageGapAdvisor:
    """Advise coverage bands for HITL review."""

    def advise(
        self,
        *,
        annual_income_need_usd: float,
        employer_life_cover_usd: float,
        planned_cover_usd: float,
    ) -> LifeInsuranceCoverageGapReport:
        """Compute coverage band.

        Args:
            annual_income_need_usd: Need amount (``> 0``).
            employer_life_cover_usd: Employer provided amount (``> 0``).
            planned_cover_usd: Planned usage/cover (``>= 0``).

        Returns:
            LifeInsuranceCoverageGapReport with ``auto_enroll=False``.

        Raises:
            ValueError: On invalid numeric inputs.
        """

        if annual_income_need_usd <= 0:
            raise ValueError("annual_income_need_usd must be > 0")
        if employer_life_cover_usd <= 0:
            raise ValueError("employer_life_cover_usd must be > 0")
        if planned_cover_usd < 0:
            raise ValueError("planned_cover_usd must be >= 0")

        covered = min(employer_life_cover_usd, planned_cover_usd)
        coverage_ratio = round(covered / annual_income_need_usd, 4)
        remaining_cap = round(max(employer_life_cover_usd - planned_cover_usd, 0.0), 2)

        if coverage_ratio >= 0.9:
            band = "well_covered"
        elif coverage_ratio >= 0.5:
            band = "partial_gap"
        else:
            band = "under_covered"

        guidance = [
            "Coverage math is advisory; verify plan documents and tax treatment.",
            "Do not auto-act from this advisor.",
        ]
        if band == "well_covered":
            guidance.append("Benefit covers most need; confirm enrollment windows.")
        elif band == "partial_gap":
            guidance.append("Partial gap; budget out-of-pocket or supplemental cover.")
        else:
            guidance.append("Benefit thin vs need; negotiate or buy supplemental cover.")

        return LifeInsuranceCoverageGapReport(
            annual_income_need_usd=float(annual_income_need_usd),
            employer_life_cover_usd=float(employer_life_cover_usd),
            planned_cover_usd=float(planned_cover_usd),
            coverage_ratio=float(coverage_ratio),
            remaining_cap=float(remaining_cap),
            coverage_band=band,
            guidance=guidance,
            requires_human_review=True,
            auto_enroll=False,
        )

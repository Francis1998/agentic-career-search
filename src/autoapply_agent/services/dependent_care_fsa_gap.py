"""HITL Dependent Care FSA gap advisor (offline; never auto-enrolls).

Closes the gap vs WageWorks/Fidelity/Levels.fyi Dependent Care FSA planners
locked in closed UIs. Emits coverage bands — never auto-enrolls and never
performs network I/O.

Distinct from ``HsaContributionGapAdvisor`` and
``FertilityBenefitGapAdvisor``. Optional later polish via
GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class DependentCareFsaGapReport:
    """Human-reviewable coverage report."""

    annual_daycare_usd: float
    dcfsa_limit_usd: float
    planned_contribution_usd: float
    coverage_ratio: float
    remaining_cap_usd: float
    coverage_band: str
    guidance: list[str]
    requires_human_review: bool
    auto_enroll: bool


class DependentCareFsaGapAdvisor:
    """Advise coverage bands for HITL review."""

    def advise(
        self,
        *,
        annual_daycare_usd: float,
        dcfsa_limit_usd: float,
        planned_contribution_usd: float,
    ) -> DependentCareFsaGapReport:
        """Compute coverage band.

        Args:
            annual_daycare_usd: Expected annual eligible daycare cost (``> 0``).
            dcfsa_limit_usd: IRS/employer Dependent Care FSA annual limit (``> 0``).
            planned_contribution_usd: Planned DCFSA contribution (``>= 0``).

        Returns:
            DependentCareFsaGapReport with ``auto_enroll=False``.

        Raises:
            ValueError: On invalid numeric inputs.
        """

        if annual_daycare_usd <= 0:
            raise ValueError("annual_daycare_usd must be > 0")
        if dcfsa_limit_usd <= 0:
            raise ValueError("dcfsa_limit_usd must be > 0")
        if planned_contribution_usd < 0:
            raise ValueError("planned_contribution_usd must be >= 0")

        covered = min(dcfsa_limit_usd, planned_contribution_usd)
        coverage_ratio = round(covered / annual_daycare_usd, 4)
        remaining_cap = round(max(dcfsa_limit_usd - planned_contribution_usd, 0.0), 2)

        if coverage_ratio >= 0.9:
            band = "well_covered"
        elif coverage_ratio >= 0.5:
            band = "partial_gap"
        else:
            band = "under_covered"

        guidance = [
            "Dependent Care FSA math is advisory; verify IRS limits.",
            "Do not auto-enroll Dependent Care FSA elections from this advisor.",
        ]
        if band == "well_covered":
            guidance.append("Contribution covers most cost; confirm providers.")
        elif band == "partial_gap":
            guidance.append("Partial coverage; plan after-tax remainder months.")
        else:
            guidance.append("Limit thin vs daycare; maximize election and backup care.")

        return DependentCareFsaGapReport(
            annual_daycare_usd=float(annual_daycare_usd),
            dcfsa_limit_usd=float(dcfsa_limit_usd),
            planned_contribution_usd=float(planned_contribution_usd),
            coverage_ratio=float(coverage_ratio),
            remaining_cap_usd=float(remaining_cap),
            coverage_band=band,
            guidance=guidance,
            requires_human_review=True,
            auto_enroll=False,
        )

"""HITL COBRA continuation cost-gap advisor (offline; never auto-enrolls).

Closes the gap vs Fidelity / HealthEquity / Levels.fyi COBRA premium
planners locked in closed UIs. Given monthly COBRA premium, months of
runway needed, and severance/cash bridge months, emits coverage bands —
never auto-enrolls and never performs network I/O.

Distinct from ``SeverancePackageGapAdvisor`` (severance weeks) and
``HsaContributionGapAdvisor`` (HSA room). Optional later polish via
GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class CobraContinuationGapReport:
    """Human-reviewable COBRA continuation coverage report."""

    monthly_premium_usd: float
    months_needed: int
    bridge_months_funded: float
    coverage_ratio: float
    total_cobra_cost_usd: float
    coverage_band: str
    guidance: list[str]
    requires_human_review: bool
    auto_enroll: bool


class CobraContinuationGapAdvisor:
    """Advise COBRA premium runway coverage vs funded bridge months."""

    def advise(
        self,
        *,
        monthly_premium_usd: float,
        months_needed: int,
        bridge_months_funded: float,
    ) -> CobraContinuationGapReport:
        """Compute COBRA continuation coverage band.

        Args:
            monthly_premium_usd: Employee COBRA monthly premium (``> 0``).
            months_needed: Months of COBRA coverage needed (``> 0``).
            bridge_months_funded: Severance/cash months that fund premiums (``>= 0``).

        Returns:
            CobraContinuationGapReport with ``auto_enroll=False``.

        Raises:
            ValueError: On invalid numeric inputs.
        """

        if monthly_premium_usd <= 0:
            raise ValueError("monthly_premium_usd must be > 0")
        if months_needed <= 0:
            raise ValueError("months_needed must be > 0")
        if bridge_months_funded < 0:
            raise ValueError("bridge_months_funded must be >= 0")

        coverage_ratio = round(bridge_months_funded / float(months_needed), 4)
        total_cost = round(monthly_premium_usd * months_needed, 2)

        if coverage_ratio >= 1.0:
            band = "fully_bridged"
        elif coverage_ratio >= 0.6:
            band = "partial_gap"
        else:
            band = "under_bridged"

        guidance = [
            "COBRA continuation math is advisory; verify carrier quotes and HR election windows.",
            "Do not auto-enroll COBRA from this advisor.",
        ]
        if band == "fully_bridged":
            guidance.append("Bridge months cover the needed runway; confirm subsidy paperwork.")
        elif band == "partial_gap":
            guidance.append(
                "Partial bridge; plan out-of-pocket months before the election deadline."
            )
        else:
            guidance.append(
                "Bridge thin vs needed months; escalate runway funding before COBRA start."
            )

        return CobraContinuationGapReport(
            monthly_premium_usd=float(monthly_premium_usd),
            months_needed=int(months_needed),
            bridge_months_funded=float(bridge_months_funded),
            coverage_ratio=float(coverage_ratio),
            total_cobra_cost_usd=float(total_cost),
            coverage_band=band,
            guidance=guidance,
            requires_human_review=True,
            auto_enroll=False,
        )

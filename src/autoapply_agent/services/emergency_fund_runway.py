"""HITL EmergencyFundRunwayAdvisor (offline; never auto-acts).

Closes the gap vs YNAB/Mint/Levels.fyi emergency-fund runway planners
locked in closed UIs. Emits runway-month bands —
never auto-acts and never performs network I/O.

Distinct from ``CobraContinuationGapAdvisor`` and
``SeverancePackageGapAdvisor``. Optional later polish via GPT-5.5 /
Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class EmergencyFundRunwayReport:
    """Human-reviewable emergency-fund runway report."""

    liquid_savings_usd: float
    monthly_burn_usd: float
    target_months: float
    runway_months: float
    coverage_ratio: float
    coverage_band: str
    guidance: list[str]
    requires_human_review: bool
    auto_enroll: bool


class EmergencyFundRunwayAdvisor:
    """Advise emergency-fund runway bands for HITL review."""

    def advise(
        self,
        *,
        liquid_savings_usd: float,
        monthly_burn_usd: float,
        target_months: float = 6.0,
    ) -> EmergencyFundRunwayReport:
        """Compute runway coverage band.

        Args:
            liquid_savings_usd: Liquid cash/equivalents (``>= 0``).
            monthly_burn_usd: Essential monthly spend (``> 0``).
            target_months: Target runway months (``> 0``).

        Returns:
            EmergencyFundRunwayReport with ``auto_enroll=False``.

        Raises:
            ValueError: On invalid numeric inputs.
        """

        if liquid_savings_usd < 0:
            raise ValueError("liquid_savings_usd must be >= 0")
        if monthly_burn_usd <= 0:
            raise ValueError("monthly_burn_usd must be > 0")
        if target_months <= 0:
            raise ValueError("target_months must be > 0")

        runway_months = round(liquid_savings_usd / monthly_burn_usd, 4)
        coverage_ratio = round(min(runway_months, target_months) / target_months, 4)

        if coverage_ratio >= 0.9:
            band = "well_covered"
        elif coverage_ratio >= 0.5:
            band = "partial_gap"
        else:
            band = "under_covered"

        guidance = [
            "Runway math is advisory; verify burn assumptions and tax buffers.",
            "Do not auto-act from this advisor.",
        ]
        if band == "well_covered":
            guidance.append("Runway near target; keep contributions steady.")
        elif band == "partial_gap":
            guidance.append("Partial gap; prioritize cash build before resigning.")
        else:
            guidance.append("Runway thin; delay unpaid gaps or cut burn.")

        return EmergencyFundRunwayReport(
            liquid_savings_usd=float(liquid_savings_usd),
            monthly_burn_usd=float(monthly_burn_usd),
            target_months=float(target_months),
            runway_months=float(runway_months),
            coverage_ratio=float(coverage_ratio),
            coverage_band=band,
            guidance=guidance,
            requires_human_review=True,
            auto_enroll=False,
        )

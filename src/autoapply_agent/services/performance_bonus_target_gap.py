"""HITL performance-bonus target gap advisor (offline; never auto-accepts).

Closes the gap vs Levels.fyi / Candor / Blind target-bonus calculators locked
in closed UIs. Given offered target bonus % of base and market target %, emits
gap bands — never auto-accepts and never performs network I/O.

Distinct from ``SalaryBandAdvisor`` (base salary) and
``FourOhOneKMatchGapAdvisor`` (401k). Optional later polish via GPT-5.5 /
Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class PerformanceBonusTargetGapReport:
    """Human-reviewable performance-bonus target gap report."""

    offered_target_pct: float
    market_target_pct: float
    gap_pct_points: float
    gap_band: str
    guidance: list[str]
    requires_human_review: bool
    auto_accept: bool


class PerformanceBonusTargetGapAdvisor:
    """Advise offered vs market performance-bonus target %."""

    def advise(
        self,
        *,
        offered_target_pct: float,
        market_target_pct: float,
    ) -> PerformanceBonusTargetGapReport:
        """Compute bonus-target gap band.

        Args:
            offered_target_pct: Offered target bonus as % of base (``>= 0``).
            market_target_pct: Market median target % (``> 0``).

        Returns:
            PerformanceBonusTargetGapReport with ``auto_accept=False``.

        Raises:
            ValueError: On invalid numeric inputs.
        """

        if offered_target_pct < 0:
            raise ValueError("offered_target_pct must be >= 0")
        if market_target_pct <= 0:
            raise ValueError("market_target_pct must be > 0")

        gap = round(offered_target_pct - market_target_pct, 4)
        # Relative shortfall vs market.
        shortfall_ratio = (market_target_pct - offered_target_pct) / market_target_pct
        if shortfall_ratio <= 0:
            band = "at_or_above_market"
        elif shortfall_ratio <= 0.2:
            band = "slight_gap"
        else:
            band = "material_gap"

        guidance = [
            "Bonus-target math is advisory; verify plan docs and payout history.",
            "Do not auto-accept offer terms from this advisor.",
        ]
        if band == "at_or_above_market":
            guidance.append("Target is at/above market; still confirm uncapped upside.")
        elif band == "slight_gap":
            guidance.append("Slight gap; negotiate a higher target or guaranteed floor.")
        else:
            guidance.append("Material gap vs market; escalate before signing.")

        return PerformanceBonusTargetGapReport(
            offered_target_pct=float(offered_target_pct),
            market_target_pct=float(market_target_pct),
            gap_pct_points=float(gap),
            gap_band=band,
            guidance=guidance,
            requires_human_review=True,
            auto_accept=False,
        )

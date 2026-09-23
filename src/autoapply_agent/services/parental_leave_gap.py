"""HITL parental-leave gap advisor (offline; never auto-accepts).

Closes the gap vs Levels.fyi / Blind / Candor parental-leave planners
locked in closed UIs. Given offered leave weeks and a market benchmark,
emits coverage bands — never auto-accepts offers and never performs
network I/O.

Distinct from ``SeverancePackageGapAdvisor`` (exit weeks) and
``RelocationPackageGapAdvisor`` (move stipend). Optional later polish
via GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class ParentalLeaveGapReport:
    """Human-reviewable parental-leave coverage report."""

    offered_weeks: float
    market_weeks: float
    coverage_ratio: float
    coverage_band: str
    guidance: list[str]
    requires_human_review: bool
    auto_accept: bool


class ParentalLeaveGapAdvisor:
    """Advise parental-leave coverage vs a market benchmark."""

    def advise(
        self,
        *,
        offered_weeks: float,
        market_weeks: float = 12.0,
    ) -> ParentalLeaveGapReport:
        """Compute leave coverage band vs market weeks.

        Args:
            offered_weeks: Paid leave weeks offered (``>= 0``).
            market_weeks: Benchmark market weeks (``> 0``).

        Returns:
            ParentalLeaveGapReport with ``auto_accept=False``.

        Raises:
            ValueError: On invalid numeric inputs.
        """

        if offered_weeks < 0:
            raise ValueError("offered_weeks must be >= 0")
        if market_weeks <= 0:
            raise ValueError("market_weeks must be > 0")

        ratio = round(offered_weeks / market_weeks, 4)
        if ratio >= 1.0:
            band = "at_or_above_market"
        elif ratio >= 0.75:
            band = "near_market"
        elif ratio >= 0.5:
            band = "below_market"
        else:
            band = "thin"

        guidance = [
            "Leave math is advisory; verify with benefits docs and counsel.",
            "Do not auto-accept from this advisor.",
        ]
        if band == "at_or_above_market":
            guidance.append("Offered leave meets or exceeds the market benchmark.")
        elif band == "near_market":
            guidance.append("Leave is near market; confirm unpaid top-ups and job protection.")
        elif band == "below_market":
            guidance.append("Leave is below market; negotiate weeks or pay continuity.")
        else:
            guidance.append("Leave looks thin (<50% of market); escalate before accepting.")

        return ParentalLeaveGapReport(
            offered_weeks=float(offered_weeks),
            market_weeks=float(market_weeks),
            coverage_ratio=float(ratio),
            coverage_band=band,
            guidance=guidance,
            requires_human_review=True,
            auto_accept=False,
        )

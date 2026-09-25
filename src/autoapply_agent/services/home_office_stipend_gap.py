"""HITL home-office stipend vs setup-cost gap advisor (offline; never auto-accepts).

Closes the gap vs Rippling / Levels.fyi / Candor home-office stipend calculators
locked in closed UIs. Given offered annual stipend USD and estimated one-time
setup cost USD, emits coverage bands — never auto-accepts and never performs
network I/O.

Distinct from ``CommuteCostTradeoffAdvisor`` (commute vs remote stipend) and
``RelocationPackageGapAdvisor`` (relocation). Optional later polish via
GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class HomeOfficeStipendGapReport:
    """Human-reviewable home-office stipend coverage report."""

    stipend_annual_usd: float
    setup_cost_usd: float
    coverage_ratio: float
    gap_usd: float
    coverage_band: str
    guidance: list[str]
    requires_human_review: bool
    auto_accept: bool


class HomeOfficeStipendGapAdvisor:
    """Advise home-office stipend vs setup-cost coverage."""

    def advise(
        self,
        *,
        stipend_annual_usd: float,
        setup_cost_usd: float,
    ) -> HomeOfficeStipendGapReport:
        """Compute stipend coverage band vs setup cost.

        Args:
            stipend_annual_usd: Offered annual home-office stipend (``>= 0``).
            setup_cost_usd: Estimated desk/monitor/chair setup cost (``> 0``).

        Returns:
            HomeOfficeStipendGapReport with ``auto_accept=False``.

        Raises:
            ValueError: On invalid numeric inputs.
        """

        if stipend_annual_usd < 0:
            raise ValueError("stipend_annual_usd must be >= 0")
        if setup_cost_usd <= 0:
            raise ValueError("setup_cost_usd must be > 0")

        coverage = round(stipend_annual_usd / setup_cost_usd, 4)
        gap = round(setup_cost_usd - stipend_annual_usd, 2)

        if coverage >= 1.0:
            band = "fully_covered"
        elif coverage >= 0.6:
            band = "partial"
        else:
            band = "underfunded"

        guidance = [
            "Home-office stipend math is advisory; verify policy and tax treatment.",
            "Do not auto-accept stipend terms from this advisor.",
        ]
        if band == "fully_covered":
            guidance.append("Stipend covers estimated setup; confirm eligible SKUs.")
        elif band == "partial":
            guidance.append("Partial coverage; negotiate a one-time equipment top-up.")
        else:
            guidance.append("Stipend is thin vs setup cost; escalate before accepting WFH terms.")

        return HomeOfficeStipendGapReport(
            stipend_annual_usd=float(stipend_annual_usd),
            setup_cost_usd=float(setup_cost_usd),
            coverage_ratio=float(coverage),
            gap_usd=float(gap),
            coverage_band=band,
            guidance=guidance,
            requires_human_review=True,
            auto_accept=False,
        )

"""HITL unused-PTO cash-out value advisor (offline; never auto-cashes).

Closes the gap vs Rippling / Gusto / Candor PTO payout calculators locked in
closed UIs. Given unused PTO hours and hourly rate, emits cash-out value
bands — never auto-cashes and never performs network I/O.

Distinct from ``SeverancePackageGapAdvisor`` (severance weeks) and
``ParentalLeaveGapAdvisor`` (leave weeks). Optional later polish via GPT-5.5 /
Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class PtoCashOutValueReport:
    """Human-reviewable PTO cash-out value report."""

    unused_pto_hours: float
    hourly_rate: float
    cash_out_usd: float
    value_band: str
    guidance: list[str]
    requires_human_review: bool
    auto_cash: bool


class PtoCashOutValueAdvisor:
    """Advise unused-PTO cash-out value at exit or year-end."""

    def advise(
        self,
        *,
        unused_pto_hours: float,
        hourly_rate: float,
    ) -> PtoCashOutValueReport:
        """Compute cash-out USD and value band.

        Args:
            unused_pto_hours: Unused PTO hours (``>= 0``).
            hourly_rate: Cash-out hourly rate USD (``> 0``).

        Returns:
            PtoCashOutValueReport with ``auto_cash=False``.

        Raises:
            ValueError: On invalid numeric inputs.
        """

        if unused_pto_hours < 0:
            raise ValueError("unused_pto_hours must be >= 0")
        if hourly_rate <= 0:
            raise ValueError("hourly_rate must be > 0")

        cash_out = round(unused_pto_hours * hourly_rate, 2)
        # Bands relative to ~1 week (40h) and ~2 weeks (80h) of pay.
        week_pay = hourly_rate * 40.0
        if cash_out >= week_pay * 2:
            band = "rich"
        elif cash_out >= week_pay:
            band = "fair"
        else:
            band = "thin"

        guidance = [
            "PTO cash-out math is advisory; verify handbook payout rules.",
            "Do not auto-cash or file payout requests from this advisor.",
        ]
        if band == "rich":
            guidance.append("Unused PTO is >=2 weeks of pay; confirm payout vs use-it policy.")
        elif band == "fair":
            guidance.append("About 1-2 weeks of pay; decide use-vs-cash before a blackout.")
        else:
            guidance.append("Under one week of pay; often better to schedule time off.")

        return PtoCashOutValueReport(
            unused_pto_hours=float(unused_pto_hours),
            hourly_rate=float(hourly_rate),
            cash_out_usd=float(cash_out),
            value_band=band,
            guidance=guidance,
            requires_human_review=True,
            auto_cash=False,
        )

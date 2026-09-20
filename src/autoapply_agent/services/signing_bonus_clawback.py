"""HITL signing-bonus clawback advisor (offline; never auto-accepts).

Closes the gap vs Levels.fyi / Candor / Blind offer calculators locked in
closed UIs. Given signing bonus, clawback months, and months elapsed, emits
remaining clawback liability bands — never auto-accepts offers and never
performs network I/O.

Distinct from ``EquityVestingCliffAdvisor`` (equity vest schedules) and
``OfferDeadlineTracker`` (acceptance deadlines). Optional later polish via
GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class SigningBonusClawbackReport:
    """Human-reviewable signing-bonus clawback liability report."""

    bonus_amount: float
    clawback_months: int
    months_elapsed: int
    remaining_liability: float
    liability_fraction: float
    clawback_band: str
    guidance: list[str]
    requires_human_review: bool
    auto_accept: bool


class SigningBonusClawbackAdvisor:
    """Advise remaining clawback liability under linear monthly burn-down."""

    def advise(
        self,
        *,
        bonus_amount: float,
        clawback_months: int = 12,
        months_elapsed: int = 0,
    ) -> SigningBonusClawbackReport:
        """Compute remaining clawback liability for a signing bonus.

        Args:
            bonus_amount: Gross signing bonus USD (``>= 0``).
            clawback_months: Full clawback horizon in months (``> 0``).
            months_elapsed: Months since start date (``>= 0``).

        Returns:
            SigningBonusClawbackReport with ``auto_accept=False``.

        Raises:
            ValueError: On invalid numeric inputs.
        """

        if bonus_amount < 0:
            raise ValueError("bonus_amount must be >= 0")
        if clawback_months <= 0:
            raise ValueError("clawback_months must be > 0")
        if months_elapsed < 0:
            raise ValueError("months_elapsed must be >= 0")

        if months_elapsed >= clawback_months:
            remaining = 0.0
            fraction = 0.0
        else:
            remaining_months = clawback_months - months_elapsed
            fraction = remaining_months / float(clawback_months)
            remaining = round(bonus_amount * fraction, 2)

        if fraction <= 0:
            band = "cleared"
        elif fraction <= 0.25:
            band = "low_liability"
        elif fraction <= 0.75:
            band = "mid_liability"
        else:
            band = "high_liability"

        guidance = [
            "Signing-bonus clawback math is advisory; verify with the offer letter.",
            "Do not auto-accept from this advisor.",
        ]
        if band == "high_liability":
            guidance.append(
                "Most of the bonus is still clawable; model repayment before resigning."
            )
        elif band == "cleared":
            guidance.append("Clawback window appears cleared under a linear schedule.")
        else:
            guidance.append(
                f"About {fraction:.0%} of the bonus remains clawable under linear burn-down."
            )

        return SigningBonusClawbackReport(
            bonus_amount=float(bonus_amount),
            clawback_months=int(clawback_months),
            months_elapsed=int(months_elapsed),
            remaining_liability=float(remaining),
            liability_fraction=float(fraction),
            clawback_band=band,
            guidance=guidance,
            requires_human_review=True,
            auto_accept=False,
        )

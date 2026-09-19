"""HITL equity vesting / cliff advisor (offline; never auto-accepts).

Closes the gap vs Levels.fyi / Candor / Carta vesting calculators locked in
closed UIs. Given grant value, cliff months, and vest months, emits vested-to-
date and next-cliff guidance — never auto-accepts offers and never performs
network I/O.

Distinct from ``OfferCompareMatrix`` (side-by-side cash+equity totals) and
``NegotiationTalkingPointsService`` (counter-offer talking points). Optional
later polish via GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 must stay
advisory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class EquityVestingReport:
    """Human-reviewable equity vesting schedule report."""

    grant_value: float
    cliff_months: int
    vest_months: int
    months_elapsed: int
    vested_value: float
    unvested_value: float
    past_cliff: bool
    vest_band: str
    guidance: list[str]
    requires_human_review: bool
    auto_accept: bool


class EquityVestingCliffAdvisor:
    """Advise linear post-cliff vesting progress for a single grant."""

    def advise(
        self,
        *,
        grant_value: float,
        cliff_months: int = 12,
        vest_months: int = 48,
        months_elapsed: int = 0,
    ) -> EquityVestingReport:
        """Compute vested/unvested value under a standard cliff + linear vest.

        Args:
            grant_value: Total grant USD (or USD-equivalent) at grant.
            cliff_months: Months before any shares vest (``>= 0``).
            vest_months: Total vest horizon including cliff (``> cliff_months``).
            months_elapsed: Months since grant start (``>= 0``).

        Returns:
            EquityVestingReport with ``auto_accept=False``.

        Raises:
            ValueError: On invalid numeric inputs.
        """

        if grant_value < 0:
            raise ValueError("grant_value must be >= 0")
        if cliff_months < 0:
            raise ValueError("cliff_months must be >= 0")
        if vest_months <= cliff_months:
            raise ValueError("vest_months must be > cliff_months")
        if months_elapsed < 0:
            raise ValueError("months_elapsed must be >= 0")

        past_cliff = months_elapsed >= cliff_months
        if months_elapsed <= 0:
            vested = 0.0
        elif not past_cliff:
            vested = 0.0
        elif months_elapsed >= vest_months:
            vested = float(grant_value)
        else:
            # Linear vest after cliff across the remaining months.
            vested_frac = months_elapsed / float(vest_months)
            vested = round(grant_value * vested_frac, 2)

        unvested = round(max(0.0, grant_value - vested), 2)
        frac = 0.0 if grant_value == 0 else vested / grant_value
        if frac >= 0.75:
            band = "mostly_vested"
        elif frac >= 0.25:
            band = "mid_vest"
        elif past_cliff and frac > 0:
            band = "early_vest"
        elif past_cliff:
            band = "at_cliff"
        else:
            band = "pre_cliff"

        guidance = [
            "Equity vesting math is advisory; verify with the offer letter.",
            "Do not auto-accept from this advisor.",
        ]
        if band == "pre_cliff":
            remaining = cliff_months - months_elapsed
            guidance.append(
                f"Cliff in ~{remaining} month(s); leaving early forfeits unvested value."
            )
        if band in {"early_vest", "mid_vest"}:
            guidance.append("Model refresh grants and dilution before negotiating.")

        return EquityVestingReport(
            grant_value=float(grant_value),
            cliff_months=int(cliff_months),
            vest_months=int(vest_months),
            months_elapsed=int(months_elapsed),
            vested_value=float(vested),
            unvested_value=float(unvested),
            past_cliff=bool(past_cliff),
            vest_band=band,
            guidance=guidance,
            requires_human_review=True,
            auto_accept=False,
        )

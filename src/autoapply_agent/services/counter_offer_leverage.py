"""HITL counter-offer leverage advisor (offline; never auto-sends).

Closes the gap vs Huntr / Teal / Levels.fyi negotiation tools locked in
closed UIs. Given current offer total-comp and a competing offer,
emits leverage bands — never auto-sends counters and never performs
network I/O.

Distinct from ``NegotiationTalkingPointsService`` (talking points) and
``OfferDeadlineTracker`` (deadline countdown). Optional later polish
via GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class CounterOfferLeverageReport:
    """Human-reviewable counter-offer leverage report."""

    current_offer_tc: float
    competing_offer_tc: float
    delta_pct: float
    leverage_band: str
    guidance: list[str]
    requires_human_review: bool
    auto_send: bool


class CounterOfferLeverageAdvisor:
    """Advise counter-offer leverage from competing total-comp."""

    def advise(
        self,
        *,
        current_offer_tc: float,
        competing_offer_tc: float,
    ) -> CounterOfferLeverageReport:
        """Compute leverage band from competing vs current TC.

        Args:
            current_offer_tc: Current offer total-comp USD (``> 0``).
            competing_offer_tc: Competing offer total-comp USD (``>= 0``).

        Returns:
            CounterOfferLeverageReport with ``auto_send=False``.

        Raises:
            ValueError: On invalid numeric inputs.
        """

        if current_offer_tc <= 0:
            raise ValueError("current_offer_tc must be > 0")
        if competing_offer_tc < 0:
            raise ValueError("competing_offer_tc must be >= 0")

        delta = round(
            (competing_offer_tc - current_offer_tc) / current_offer_tc * 100.0,
            2,
        )
        if competing_offer_tc <= 0:
            band = "none"
        elif delta >= 15.0:
            band = "strong"
        elif delta >= 5.0:
            band = "moderate"
        elif delta > 0:
            band = "soft"
        else:
            band = "weak"

        guidance = [
            "Leverage math is advisory; verify offers in writing.",
            "Do not auto-send counters from this advisor.",
        ]
        if band == "strong":
            guidance.append("Competing offer is >=15% higher; strong leverage for a counter.")
        elif band == "moderate":
            guidance.append("Moderate leverage; ask for a targeted bump or equity top-up.")
        elif band == "soft":
            guidance.append("Soft leverage; prefer non-cash asks if cash room is tight.")
        elif band == "weak":
            guidance.append("Competing offer is not higher; lean on role fit, not price.")
        else:
            guidance.append("No competing offer on file; avoid fabricating leverage.")

        return CounterOfferLeverageReport(
            current_offer_tc=float(current_offer_tc),
            competing_offer_tc=float(competing_offer_tc),
            delta_pct=float(delta),
            leverage_band=band,
            guidance=guidance,
            requires_human_review=True,
            auto_send=False,
        )

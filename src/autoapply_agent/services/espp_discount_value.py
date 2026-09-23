"""HITL ESPP discount value advisor (offline; never auto-enrolls).

Closes the gap vs Levels.fyi / Carta / Candor ESPP planners locked in
closed UIs. Given contribution USD, discount percent, and lookback
uplift, emits value bands — never auto-enrolls and never performs
network I/O.

Distinct from ``EquityVestingCliffAdvisor`` (grant vesting) and
``RsuRefreshCadenceAdvisor`` (refresh cadence). Optional later polish
via GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class EsppDiscountValueReport:
    """Human-reviewable ESPP discount value report."""

    contribution_usd: float
    discount_pct: float
    lookback_uplift_pct: float
    estimated_value_usd: float
    value_band: str
    guidance: list[str]
    requires_human_review: bool
    auto_enroll: bool


class EsppDiscountValueAdvisor:
    """Advise ESPP look-through discount value from contribution inputs."""

    def advise(
        self,
        *,
        contribution_usd: float,
        discount_pct: float = 15.0,
        lookback_uplift_pct: float = 0.0,
    ) -> EsppDiscountValueReport:
        """Compute ESPP discount value band.

        Args:
            contribution_usd: Planned purchase contribution (``>= 0``).
            discount_pct: Plan discount percent in ``[0, 100]``.
            lookback_uplift_pct: Extra lookback benefit percent (``>= 0``).

        Returns:
            EsppDiscountValueReport with ``auto_enroll=False``.

        Raises:
            ValueError: On invalid numeric inputs.
        """

        if contribution_usd < 0:
            raise ValueError("contribution_usd must be >= 0")
        if not 0.0 <= discount_pct <= 100.0:
            raise ValueError("discount_pct must be in [0, 100]")
        if lookback_uplift_pct < 0:
            raise ValueError("lookback_uplift_pct must be >= 0")

        effective = (discount_pct + lookback_uplift_pct) / 100.0
        value = round(contribution_usd * effective, 2)
        if value >= 2_000:
            band = "high"
        elif value >= 750:
            band = "moderate"
        elif value > 0:
            band = "low"
        else:
            band = "none"

        guidance = [
            "ESPP math is advisory; verify with plan docs and tax counsel.",
            "Do not auto-enroll from this advisor.",
        ]
        if band == "high":
            guidance.append("Discount value looks material; confirm cash-flow before maxing.")
        elif band == "moderate":
            guidance.append("Moderate discount value; weigh vs emergency-fund needs.")
        elif band == "low":
            guidance.append("Low absolute value; still useful if cash-flow allows.")
        else:
            guidance.append("No discount value detected; confirm plan parameters.")

        return EsppDiscountValueReport(
            contribution_usd=float(contribution_usd),
            discount_pct=float(discount_pct),
            lookback_uplift_pct=float(lookback_uplift_pct),
            estimated_value_usd=float(value),
            value_band=band,
            guidance=guidance,
            requires_human_review=True,
            auto_enroll=False,
        )

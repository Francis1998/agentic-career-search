"""HITL ISO bargain-element AMT exposure advisor (offline; never auto-exercises).

Closes the gap vs Carta / Pulley / Levels.fyi ISO AMT calculators locked in
closed UIs. Given shares exercised, FMV, strike, and a modeled AMT exemption,
emits bargain-element exposure bands — never auto-exercises and never
performs network I/O.

Distinct from ``EquityVestingCliffAdvisor`` (vest schedules) and
``EsppDiscountValueAdvisor`` (ESPP). Optional later polish via
GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class IsoAmtExposureReport:
    """Human-reviewable ISO AMT exposure report."""

    shares_exercised: int
    fmv_at_exercise: float
    strike_price: float
    amt_exemption_usd: float
    bargain_element_usd: float
    exposure_ratio: float
    exposure_band: str
    guidance: list[str]
    requires_human_review: bool
    auto_exercise: bool


class IsoAmtExposureAdvisor:
    """Advise ISO exercise bargain-element exposure vs a modeled AMT exemption."""

    def advise(
        self,
        *,
        shares_exercised: int,
        fmv_at_exercise: float,
        strike_price: float,
        amt_exemption_usd: float,
    ) -> IsoAmtExposureReport:
        """Compute ISO bargain-element AMT exposure band.

        Args:
            shares_exercised: ISO shares exercised (``>= 0``).
            fmv_at_exercise: Fair market value per share at exercise (``>= 0``).
            strike_price: Option strike per share (``>= 0``).
            amt_exemption_usd: Modeled AMT exemption USD (``> 0``).

        Returns:
            IsoAmtExposureReport with ``auto_exercise=False``.

        Raises:
            ValueError: On invalid numeric inputs.
        """

        if shares_exercised < 0:
            raise ValueError("shares_exercised must be >= 0")
        if fmv_at_exercise < 0:
            raise ValueError("fmv_at_exercise must be >= 0")
        if strike_price < 0:
            raise ValueError("strike_price must be >= 0")
        if amt_exemption_usd <= 0:
            raise ValueError("amt_exemption_usd must be > 0")
        if fmv_at_exercise < strike_price:
            raise ValueError("fmv_at_exercise must be >= strike_price")

        spread = fmv_at_exercise - strike_price
        bargain = round(shares_exercised * spread, 2)
        ratio = round(bargain / amt_exemption_usd, 4)

        if ratio >= 1.0:
            band = "high_exposure"
        elif ratio >= 0.25:
            band = "moderate_exposure"
        else:
            band = "low_exposure"

        guidance = [
            "ISO AMT math is advisory; verify with a tax advisor and Form 6251.",
            "Do not auto-exercise ISOs from this advisor.",
        ]
        if band == "high_exposure":
            guidance.append("Bargain element meets/exceeds modeled exemption; stage exercises.")
        elif band == "moderate_exposure":
            guidance.append("Material AMT exposure; model quarterly estimated payments.")
        else:
            guidance.append("Bargain element is small vs modeled exemption.")

        return IsoAmtExposureReport(
            shares_exercised=int(shares_exercised),
            fmv_at_exercise=float(fmv_at_exercise),
            strike_price=float(strike_price),
            amt_exemption_usd=float(amt_exemption_usd),
            bargain_element_usd=float(bargain),
            exposure_ratio=float(ratio),
            exposure_band=band,
            guidance=guidance,
            requires_human_review=True,
            auto_exercise=False,
        )

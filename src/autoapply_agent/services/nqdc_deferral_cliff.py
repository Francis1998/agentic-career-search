"""HITL NQDC deferral cliff advisor (offline; never auto-elects).

Closes the gap vs Fidelity / Carta / Levels.fyi deferred-comp (NQDC)
distribution planners locked in closed UIs. Given years until cliff,
elected deferral USD, and projected tax-rate delta at distribution,
emits cliff-risk bands — never auto-elects and never performs network I/O.

Distinct from ``EquityVestingCliffAdvisor`` (equity vest) and
``IsoAmtExposureAdvisor`` (ISO AMT). Optional later polish via
GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class NqdcDeferralCliffReport:
    """Human-reviewable NQDC deferral cliff report."""

    years_to_cliff: float
    deferral_usd: float
    tax_rate_delta: float
    cliff_pressure: float
    cliff_band: str
    guidance: list[str]
    requires_human_review: bool
    auto_elect: bool


class NqdcDeferralCliffAdvisor:
    """Advise NQDC deferral cliff risk from timing and tax-rate delta."""

    def advise(
        self,
        *,
        years_to_cliff: float,
        deferral_usd: float,
        tax_rate_delta: float,
    ) -> NqdcDeferralCliffReport:
        """Compute NQDC deferral cliff band.

        Args:
            years_to_cliff: Years until scheduled distribution (``>= 0``).
            deferral_usd: Deferred amount in USD (``> 0``).
            tax_rate_delta: Expected tax-rate change at distribution
                (can be negative; absolute value used for pressure).

        Returns:
            NqdcDeferralCliffReport with ``auto_elect=False``.

        Raises:
            ValueError: On invalid numeric inputs.
        """

        if years_to_cliff < 0:
            raise ValueError("years_to_cliff must be >= 0")
        if deferral_usd <= 0:
            raise ValueError("deferral_usd must be > 0")

        # Nearer cliffs + large deferrals + adverse rate deltas raise pressure.
        proximity = 1.0 / max(years_to_cliff, 0.25)
        rate_factor = 1.0 + abs(float(tax_rate_delta))
        cliff_pressure = round(proximity * (deferral_usd / 100_000.0) * rate_factor, 4)

        if cliff_pressure >= 4.0 or years_to_cliff <= 1.0:
            band = "cliff_urgent"
        elif cliff_pressure >= 1.5 or years_to_cliff <= 3.0:
            band = "cliff_watch"
        else:
            band = "cliff_calm"

        guidance = [
            "NQDC cliff math is advisory; verify plan docs and distribution elections.",
            "Do not auto-elect NQDC deferrals or distributions from this advisor.",
        ]
        if band == "cliff_urgent":
            guidance.append(
                "Cliff is near or pressure high; review distribution timing with tax counsel."
            )
        elif band == "cliff_watch":
            guidance.append(
                "Monitor deferral schedule; model tax-rate scenarios before election windows."
            )
        else:
            guidance.append(
                "Cliff distant; keep annual election checklist and beneficiary updates."
            )

        return NqdcDeferralCliffReport(
            years_to_cliff=float(years_to_cliff),
            deferral_usd=float(deferral_usd),
            tax_rate_delta=float(tax_rate_delta),
            cliff_pressure=float(cliff_pressure),
            cliff_band=band,
            guidance=guidance,
            requires_human_review=True,
            auto_elect=False,
        )

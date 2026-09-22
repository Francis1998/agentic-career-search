"""HITL RSU refresh cadence advisor (offline; never auto-accepts).

Closes the gap vs Levels.fyi / Carta / Candor refresh planners locked in
closed UIs. Given annual refresh target, years since last refresh, and
vesting years, emits cadence bands — never auto-accepts offers and never
performs network I/O.

Distinct from ``EquityVestingCliffAdvisor`` (initial grant vesting) and
``SigningBonusClawbackAdvisor`` (cash clawback). Optional later polish via
GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class RsuRefreshCadenceReport:
    """Human-reviewable RSU refresh cadence report."""

    annual_refresh_value: float
    years_since_refresh: float
    vesting_years: float
    accrued_value: float
    cadence_band: str
    guidance: list[str]
    requires_human_review: bool
    auto_accept: bool


class RsuRefreshCadenceAdvisor:
    """Advise RSU refresh urgency from years since last grant."""

    def advise(
        self,
        *,
        annual_refresh_value: float,
        years_since_refresh: float,
        vesting_years: float = 4.0,
    ) -> RsuRefreshCadenceReport:
        """Compute refresh cadence band and accrued heuristic value.

        Args:
            annual_refresh_value: Target annual refresh USD (``>= 0``).
            years_since_refresh: Years since last refresh (``>= 0``).
            vesting_years: Vesting horizon for a refresh grant (``> 0``).

        Returns:
            RsuRefreshCadenceReport with ``auto_accept=False``.

        Raises:
            ValueError: On invalid numeric inputs.
        """

        if annual_refresh_value < 0:
            raise ValueError("annual_refresh_value must be >= 0")
        if years_since_refresh < 0:
            raise ValueError("years_since_refresh must be >= 0")
        if vesting_years <= 0:
            raise ValueError("vesting_years must be > 0")

        accrued = round(annual_refresh_value * years_since_refresh, 2)

        if years_since_refresh < 0.75:
            band = "on_cadence"
        elif years_since_refresh < 1.25:
            band = "due_soon"
        elif years_since_refresh < 2.0:
            band = "overdue"
        else:
            band = "stale"

        guidance = [
            "Refresh math is advisory; verify with equity plan docs.",
            "Do not auto-accept from this advisor.",
        ]
        if band == "on_cadence":
            guidance.append("Refresh timing looks on cadence under a yearly heuristic.")
        elif band == "due_soon":
            guidance.append("Refresh window is approaching; prepare comp conversation.")
        elif band == "overdue":
            guidance.append(f"About ${accrued:,.0f} of target refresh value has accrued unpaid.")
        else:
            guidance.append("Refresh looks stale (>2y); negotiate catch-up grant or cash bridge.")

        return RsuRefreshCadenceReport(
            annual_refresh_value=float(annual_refresh_value),
            years_since_refresh=float(years_since_refresh),
            vesting_years=float(vesting_years),
            accrued_value=float(accrued),
            cadence_band=band,
            guidance=guidance,
            requires_human_review=True,
            auto_accept=False,
        )

"""HITL ColAdjustedOfferAdvisor (offline; never auto-acts).

Closes closed-UI planner gaps with coverage bands.
Never auto-acts and never performs network I/O.
Distinct from `OfferCompareService` and `SalaryBandAdvisor`.
Optional later polish via frontier LLMs must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class ColAdjustedOfferReport:
    """Human-reviewable report."""

    offer_usd: float
    col_adjusted_target_usd: float
    coverage_ratio: float
    remaining_cap: float
    coverage_band: str
    guidance: list[str]
    requires_human_review: bool
    auto_enroll: bool


class ColAdjustedOfferAdvisor:
    """Advise coverage bands for HITL review."""

    def advise(
        self,
        *,
        offer_usd: float,
        col_adjusted_target_usd: float,
    ) -> ColAdjustedOfferReport:
        """Compute coverage band.

        Args:
            offer_usd: Observed metric (``> 0``).
            col_adjusted_target_usd: Target value (``> 0``).

        Returns:
            ColAdjustedOfferReport with ``auto_enroll=False``.

        Raises:
            ValueError: On invalid numeric inputs.
        """

        if offer_usd <= 0:
            raise ValueError("offer_usd must be > 0")
        if col_adjusted_target_usd <= 0:
            raise ValueError("col_adjusted_target_usd must be > 0")

        coverage_ratio = round(
            min(offer_usd, col_adjusted_target_usd) / col_adjusted_target_usd,
            4,
        )
        remaining_cap = round(max(offer_usd - col_adjusted_target_usd, 0.0), 2)

        if coverage_ratio >= 0.9:
            band = "well_covered"
        elif coverage_ratio >= 0.5:
            band = "partial_gap"
        else:
            band = "under_covered"

        guidance = [
            "Advisory math only; verify against primary sources.",
            "Do not auto-act from this advisor.",
        ]
        if band == "well_covered":
            guidance.append("Coverage looks adequate for HITL confirmation.")
        elif band == "partial_gap":
            guidance.append("Partial gap; renegotiate or top-up before accepting.")
        else:
            guidance.append("Under-covered; escalate for human decision.")

        return ColAdjustedOfferReport(
            offer_usd=float(offer_usd),
            col_adjusted_target_usd=float(col_adjusted_target_usd),
            coverage_ratio=float(coverage_ratio),
            remaining_cap=float(remaining_cap),
            coverage_band=band,
            guidance=guidance,
            requires_human_review=True,
            auto_enroll=False,
        )

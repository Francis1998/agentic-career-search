"""HITL EsppLookbackGapAdvisor (offline; never auto-acts).

Closes closed-UI planner gaps with coverage bands.
Never auto-acts and never performs network I/O.
Distinct from `EsppDiscountValueAdvisor` and `EquityVestingAdvisor`.
Optional later polish via frontier LLMs must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class EsppLookbackGapReport:
    """Human-reviewable report."""

    lookback_discount_pct: float
    target_discount_pct: float
    coverage_ratio: float
    remaining_cap: float
    coverage_band: str
    guidance: list[str]
    requires_human_review: bool
    auto_enroll: bool


class EsppLookbackGapAdvisor:
    """Advise ESPP lookback discount coverage bands for HITL review."""

    def advise(
        self,
        *,
        lookback_discount_pct: float,
        target_discount_pct: float,
    ) -> EsppLookbackGapReport:
        """Compute coverage band.

        Args:
            lookback_discount_pct: Effective lookback discount percent (``> 0``).
            target_discount_pct: Target discount percent (``> 0``).

        Returns:
            EsppLookbackGapReport with ``auto_enroll=False``.

        Raises:
            ValueError: On invalid numeric inputs.
        """

        if lookback_discount_pct <= 0:
            raise ValueError("lookback_discount_pct must be > 0")
        if target_discount_pct <= 0:
            raise ValueError("target_discount_pct must be > 0")

        coverage_ratio = round(
            min(lookback_discount_pct, target_discount_pct) / target_discount_pct,
            4,
        )
        remaining_cap = round(
            max(lookback_discount_pct - target_discount_pct, 0.0),
            2,
        )

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
            guidance.append("ESPP lookback discount looks adequate for HITL confirmation.")
        elif band == "partial_gap":
            guidance.append("Partial lookback gap; renegotiate contribution or plan terms.")
        else:
            guidance.append("Under-covered lookback; escalate for human decision.")

        return EsppLookbackGapReport(
            lookback_discount_pct=float(lookback_discount_pct),
            target_discount_pct=float(target_discount_pct),
            coverage_ratio=float(coverage_ratio),
            remaining_cap=float(remaining_cap),
            coverage_band=band,
            guidance=guidance,
            requires_human_review=True,
            auto_enroll=False,
        )

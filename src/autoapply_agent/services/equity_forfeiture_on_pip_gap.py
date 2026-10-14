"""HITL EquityForfeitureOnPipGapAdvisor (offline; never auto-acts).

Closes closed-UI planner gaps with coverage bands.
Never auto-acts and never performs network I/O.
Distinct from `EquityVestingCliffAdvisor` / `EquityBlackoutWindowAdvisor`.
Optional later polish via frontier LLMs must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class EquityForfeitureOnPipGapReport:
    """Human-reviewable report."""

    protected_equity_usd: float
    unvested_equity_usd: float
    coverage_ratio: float
    remaining_cap: float
    coverage_band: str
    guidance: list[str]
    requires_human_review: bool
    auto_enroll: bool


class EquityForfeitureOnPipGapAdvisor:
    """Advise coverage bands for HITL review."""

    def advise(
        self,
        *,
        protected_equity_usd: float,
        unvested_equity_usd: float,
    ) -> EquityForfeitureOnPipGapReport:
        """Compute coverage band.

        Args:
            protected_equity_usd: Observed value (>= 0).
            unvested_equity_usd: Target value (> 0).

        Returns:
            EquityForfeitureOnPipGapReport with auto_enroll=False.

        Raises:
            ValueError: On invalid numeric inputs.
        """

        if protected_equity_usd < 0:
            raise ValueError("protected_equity_usd must be >= 0")
        if unvested_equity_usd <= 0:
            raise ValueError("unvested_equity_usd must be > 0")

        coverage_ratio = round(
            min(protected_equity_usd, unvested_equity_usd) / unvested_equity_usd, 4
        )
        remaining_cap = round(max(unvested_equity_usd - protected_equity_usd, 0.0), 2)

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
            guidance.append("Partial gap; renegotiate terms carefully.")
        else:
            guidance.append("Under-covered; escalate for human decision.")

        return EquityForfeitureOnPipGapReport(
            protected_equity_usd=float(protected_equity_usd),
            unvested_equity_usd=float(unvested_equity_usd),
            coverage_ratio=float(coverage_ratio),
            remaining_cap=float(remaining_cap),
            coverage_band=band,
            guidance=guidance,
            requires_human_review=True,
            auto_enroll=False,
        )

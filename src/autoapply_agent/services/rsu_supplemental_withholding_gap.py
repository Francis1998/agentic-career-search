"""HITL RsuSupplementalWithholdingGapAdvisor (offline; never auto-acts).

Closes closed-UI planner gaps with coverage bands.
Never auto-acts and never performs network I/O.
Distinct from `RsuRefreshCliffAdvisor` / `TaxEqualizationGrossUpAdvisor`.
Optional later polish via frontier LLMs must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class RsuSupplementalWithholdingGapReport:
    """Human-reviewable report."""

    withheld_rate: float
    marginal_rate: float
    coverage_ratio: float
    remaining_cap: float
    coverage_band: str
    guidance: list[str]
    requires_human_review: bool
    auto_enroll: bool


class RsuSupplementalWithholdingGapAdvisor:
    """Advise coverage bands for HITL review."""

    def advise(
        self,
        *,
        withheld_rate: float,
        marginal_rate: float,
    ) -> RsuSupplementalWithholdingGapReport:
        """Compute coverage band.

        Args:
            withheld_rate: Observed value (>= 0).
            marginal_rate: Target value (> 0).

        Returns:
            RsuSupplementalWithholdingGapReport with auto_enroll=False.

        Raises:
            ValueError: On invalid numeric inputs.
        """

        if withheld_rate < 0:
            raise ValueError("withheld_rate must be >= 0")
        if marginal_rate <= 0:
            raise ValueError("marginal_rate must be > 0")

        coverage_ratio = round(min(withheld_rate, marginal_rate) / marginal_rate, 4)
        remaining_cap = round(max(marginal_rate - withheld_rate, 0.0), 2)

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

        return RsuSupplementalWithholdingGapReport(
            withheld_rate=float(withheld_rate),
            marginal_rate=float(marginal_rate),
            coverage_ratio=float(coverage_ratio),
            remaining_cap=float(remaining_cap),
            coverage_band=band,
            guidance=guidance,
            requires_human_review=True,
            auto_enroll=False,
        )

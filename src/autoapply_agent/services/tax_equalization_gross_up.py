"""HITL TaxEqualizationGrossUpAdvisor (offline; never auto-acts).

Closes closed-UI planner gaps with coverage bands.
Never auto-acts and never performs network I/O.
Distinct from `RelocationPackageGapAdvisor` and `RemoteWorkStipendTaxGapAdvisor`.
Optional later polish via frontier LLMs must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class TaxEqualizationGrossUpReport:
    """Human-reviewable report."""

    gross_up_usd: float
    tax_delta_usd: float
    coverage_ratio: float
    remaining_cap: float
    coverage_band: str
    guidance: list[str]
    requires_human_review: bool
    auto_enroll: bool


class TaxEqualizationGrossUpAdvisor:
    """Advise coverage bands for HITL review."""

    def advise(
        self,
        *,
        gross_up_usd: float,
        tax_delta_usd: float,
    ) -> TaxEqualizationGrossUpReport:
        """Compute coverage band.

        Args:
            gross_up_usd: Observed available quantity (``> 0``).
            tax_delta_usd: Required quantity (``> 0``).

        Returns:
            TaxEqualizationGrossUpReport with ``auto_enroll=False``.

        Raises:
            ValueError: On invalid numeric inputs.
        """

        if gross_up_usd <= 0:
            raise ValueError("gross_up_usd must be > 0")
        if tax_delta_usd <= 0:
            raise ValueError("tax_delta_usd must be > 0")

        coverage_ratio = round(
            min(gross_up_usd, tax_delta_usd) / tax_delta_usd,
            4,
        )
        remaining_cap = round(max(gross_up_usd - tax_delta_usd, 0.0), 2)

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

        return TaxEqualizationGrossUpReport(
            gross_up_usd=float(gross_up_usd),
            tax_delta_usd=float(tax_delta_usd),
            coverage_ratio=float(coverage_ratio),
            remaining_cap=float(remaining_cap),
            coverage_band=band,
            guidance=guidance,
            requires_human_review=True,
            auto_enroll=False,
        )

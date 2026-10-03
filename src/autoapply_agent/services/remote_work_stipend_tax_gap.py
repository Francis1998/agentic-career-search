"""HITL RemoteWorkStipendTaxGapAdvisor (offline; never auto-acts).

Closes the gap vs Rippling/Gusto/Levels.fyi remote-stipend tax planners
locked in closed UIs. Emits net-stipend coverage bands —
never auto-acts and never performs network I/O.

Distinct from ``HomeOfficeStipendGapAdvisor`` and
``WellnessStipendGapAdvisor``. Optional later polish via GPT-5.5 /
Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class RemoteWorkStipendTaxGapReport:
    """Human-reviewable remote stipend tax report."""

    annual_stipend_usd: float
    estimated_tax_usd: float
    planned_net_usd: float
    coverage_ratio: float
    remaining_cap: float
    coverage_band: str
    guidance: list[str]
    requires_human_review: bool
    auto_enroll: bool


class RemoteWorkStipendTaxGapAdvisor:
    """Advise remote stipend tax-gap bands for HITL review."""

    def advise(
        self,
        *,
        annual_stipend_usd: float,
        estimated_tax_usd: float,
        planned_net_usd: float,
    ) -> RemoteWorkStipendTaxGapReport:
        """Compute net-stipend coverage band.

        Args:
            annual_stipend_usd: Gross annual stipend (``> 0``).
            estimated_tax_usd: Estimated tax on stipend (``>= 0``).
            planned_net_usd: Planned net spend from stipend (``>= 0``).

        Returns:
            RemoteWorkStipendTaxGapReport with ``auto_enroll=False``.

        Raises:
            ValueError: On invalid numeric inputs.
        """

        if annual_stipend_usd <= 0:
            raise ValueError("annual_stipend_usd must be > 0")
        if estimated_tax_usd < 0:
            raise ValueError("estimated_tax_usd must be >= 0")
        if planned_net_usd < 0:
            raise ValueError("planned_net_usd must be >= 0")
        if estimated_tax_usd > annual_stipend_usd:
            raise ValueError("estimated_tax_usd must be <= annual_stipend_usd")

        net_available = annual_stipend_usd - estimated_tax_usd
        covered = min(net_available, planned_net_usd)
        coverage_ratio = round(covered / annual_stipend_usd, 4) if annual_stipend_usd else 0.0
        # Prefer net-need coverage when planned_net > 0
        if planned_net_usd > 0:
            coverage_ratio = round(min(net_available, planned_net_usd) / planned_net_usd, 4)
        remaining_cap = round(max(net_available - planned_net_usd, 0.0), 2)

        if coverage_ratio >= 0.9:
            band = "well_covered"
        elif coverage_ratio >= 0.5:
            band = "partial_gap"
        else:
            band = "under_covered"

        guidance = [
            "Tax math is advisory; verify withholding class and state rules.",
            "Do not auto-act from this advisor.",
        ]
        if band == "well_covered":
            guidance.append("Net stipend covers planned spend after tax.")
        elif band == "partial_gap":
            guidance.append("Partial gap; trim setup spend or ask for gross-up.")
        else:
            guidance.append("Tax bite leaves stipend thin; renegotiate or defer purchases.")

        return RemoteWorkStipendTaxGapReport(
            annual_stipend_usd=float(annual_stipend_usd),
            estimated_tax_usd=float(estimated_tax_usd),
            planned_net_usd=float(planned_net_usd),
            coverage_ratio=float(coverage_ratio),
            remaining_cap=float(remaining_cap),
            coverage_band=band,
            guidance=guidance,
            requires_human_review=True,
            auto_enroll=False,
        )

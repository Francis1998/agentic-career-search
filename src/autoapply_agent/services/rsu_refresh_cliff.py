"""HITL RsuRefreshCliffAdvisor (offline; never auto-acts).

Closes closed-UI planner gaps with coverage bands.
Never auto-acts and never performs network I/O.
Distinct from `RsuRefreshCadenceAdvisor` and `EquityVestingAdvisor`.
Optional later polish via frontier LLMs must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class RsuRefreshCliffReport:
    """Human-reviewable report."""

    months_to_refresh_cliff: float
    target_buffer_months: float
    coverage_ratio: float
    remaining_cap: float
    coverage_band: str
    guidance: list[str]
    requires_human_review: bool
    auto_enroll: bool


class RsuRefreshCliffAdvisor:
    """Advise coverage bands for HITL review."""

    def advise(
        self,
        *,
        months_to_refresh_cliff: float,
        target_buffer_months: float,
    ) -> RsuRefreshCliffReport:
        """Compute coverage band.

        Args:
            months_to_refresh_cliff: Months until next RSU refresh cliff (``> 0``).
            target_buffer_months: Desired buffer before resigning (``> 0``).

        Returns:
            RsuRefreshCliffReport with ``auto_enroll=False``.

        Raises:
            ValueError: On invalid numeric inputs.
        """

        if months_to_refresh_cliff <= 0:
            raise ValueError("months_to_refresh_cliff must be > 0")
        if target_buffer_months <= 0:
            raise ValueError("target_buffer_months must be > 0")

        coverage_ratio = round(
            min(months_to_refresh_cliff, target_buffer_months) / target_buffer_months,
            4,
        )
        remaining_cap = round(
            max(months_to_refresh_cliff - target_buffer_months, 0.0),
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
            guidance.append("Refresh-cliff buffer looks adequate for HITL confirmation.")
        elif band == "partial_gap":
            guidance.append("Partial cliff gap; renegotiate timing before resigning.")
        else:
            guidance.append("Under-buffered vs refresh cliff; escalate for human decision.")

        return RsuRefreshCliffReport(
            months_to_refresh_cliff=float(months_to_refresh_cliff),
            target_buffer_months=float(target_buffer_months),
            coverage_ratio=float(coverage_ratio),
            remaining_cap=float(remaining_cap),
            coverage_band=band,
            guidance=guidance,
            requires_human_review=True,
            auto_enroll=False,
        )

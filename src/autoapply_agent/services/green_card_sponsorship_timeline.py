"""HITL GreenCardSponsorshipTimelineAdvisor (offline; never auto-acts).

Closes closed-UI planner gaps with coverage bands.
Never auto-acts and never performs network I/O.
Distinct from `VisaTimelineGapAdvisor` and `H1bLotteryOddsAdvisor`.
Optional later polish via frontier LLMs must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class GreenCardSponsorshipTimelineReport:
    """Human-reviewable report."""

    sponsored_months: float
    wait_months: float
    coverage_ratio: float
    remaining_cap: float
    coverage_band: str
    guidance: list[str]
    requires_human_review: bool
    auto_enroll: bool


class GreenCardSponsorshipTimelineAdvisor:
    """Advise coverage bands for HITL review."""

    def advise(
        self,
        *,
        sponsored_months: float,
        wait_months: float,
    ) -> GreenCardSponsorshipTimelineReport:
        """Compute coverage band.

        Args:
            sponsored_months: Observed available quantity (``> 0``).
            wait_months: Required quantity (``> 0``).

        Returns:
            GreenCardSponsorshipTimelineReport with ``auto_enroll=False``.

        Raises:
            ValueError: On invalid numeric inputs.
        """

        if sponsored_months <= 0:
            raise ValueError("sponsored_months must be > 0")
        if wait_months <= 0:
            raise ValueError("wait_months must be > 0")

        coverage_ratio = round(
            min(sponsored_months, wait_months) / wait_months,
            4,
        )
        remaining_cap = round(max(sponsored_months - wait_months, 0.0), 2)

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

        return GreenCardSponsorshipTimelineReport(
            sponsored_months=float(sponsored_months),
            wait_months=float(wait_months),
            coverage_ratio=float(coverage_ratio),
            remaining_cap=float(remaining_cap),
            coverage_band=band,
            guidance=guidance,
            requires_human_review=True,
            auto_enroll=False,
        )

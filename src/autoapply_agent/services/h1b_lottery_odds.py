"""HITL H1bLotteryOddsAdvisor (offline; never auto-acts).

Closes closed-UI planner gaps with coverage bands.
Never auto-acts and never performs network I/O.
Distinct from `VisaTimelineGapAdvisor` and `VisaSponsorshipSignalExtractor`.
Optional later polish via frontier LLMs must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class H1bLotteryOddsReport:
    """Human-reviewable report."""

    selected_registrations: float
    target_registrations: float
    coverage_ratio: float
    remaining_cap: float
    coverage_band: str
    guidance: list[str]
    requires_human_review: bool
    auto_enroll: bool


class H1bLotteryOddsAdvisor:
    """Advise coverage bands for HITL review."""

    def advise(
        self,
        *,
        selected_registrations: float,
        target_registrations: float,
    ) -> H1bLotteryOddsReport:
        """Compute coverage band.

        Args:
            selected_registrations: Observed available quantity (``> 0``).
            target_registrations: Required quantity (``> 0``).

        Returns:
            H1bLotteryOddsReport with ``auto_enroll=False``.

        Raises:
            ValueError: On invalid numeric inputs.
        """

        if selected_registrations <= 0:
            raise ValueError("selected_registrations must be > 0")
        if target_registrations <= 0:
            raise ValueError("target_registrations must be > 0")

        coverage_ratio = round(
            min(selected_registrations, target_registrations) / target_registrations,
            4,
        )
        remaining_cap = round(max(selected_registrations - target_registrations, 0.0), 2)

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

        return H1bLotteryOddsReport(
            selected_registrations=float(selected_registrations),
            target_registrations=float(target_registrations),
            coverage_ratio=float(coverage_ratio),
            remaining_cap=float(remaining_cap),
            coverage_band=band,
            guidance=guidance,
            requires_human_review=True,
            auto_enroll=False,
        )

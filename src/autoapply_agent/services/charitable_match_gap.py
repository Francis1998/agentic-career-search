"""HITL CharitableMatchGapAdvisor (offline; never auto-acts).

Closes closed-UI planner gaps with coverage bands.
Never auto-acts and never performs network I/O.
Distinct from `EmployeeVolunteerHoursGapAdvisor` / `WellnessStipendGapAdvisor`.
Gap vs Benevity/YourCause/CyberGrants charitable-match planners.
Optional later polish via frontier LLMs must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class CharitableMatchGapReport:
    """Human-reviewable report."""

    match_usd: float
    donation_usd: float
    coverage_ratio: float
    remaining_cap: float
    coverage_band: str
    guidance: list[str]
    requires_human_review: bool
    auto_enroll: bool


class CharitableMatchGapAdvisor:
    """Advise coverage bands for HITL review."""

    def advise(
        self,
        *,
        match_usd: float,
        donation_usd: float,
    ) -> CharitableMatchGapReport:
        """Compute coverage band.

        Args:
            match_usd: Observed value (>= 0).
            donation_usd: Target value (> 0).

        Returns:
            CharitableMatchGapReport with auto_enroll=False.

        Raises:
            ValueError: On invalid numeric inputs.
        """

        if match_usd < 0:
            raise ValueError("match_usd must be >= 0")
        if donation_usd <= 0:
            raise ValueError("donation_usd must be > 0")

        coverage_ratio = round(min(match_usd, donation_usd) / donation_usd, 4)
        remaining_cap = round(max(donation_usd - match_usd, 0.0), 2)

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

        return CharitableMatchGapReport(
            match_usd=float(match_usd),
            donation_usd=float(donation_usd),
            coverage_ratio=float(coverage_ratio),
            remaining_cap=float(remaining_cap),
            coverage_band=band,
            guidance=guidance,
            requires_human_review=True,
            auto_enroll=False,
        )

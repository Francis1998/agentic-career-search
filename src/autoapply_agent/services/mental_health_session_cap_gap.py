"""HITL MentalHealthSessionCapGapAdvisor (offline; never auto-acts).

Closes closed-UI planner gaps with coverage bands.
Never auto-acts and never performs network I/O.
Distinct from `MentalHealthEapSessionGapAdvisor` / `WellnessStipendGapAdvisor`.
Gap vs Lyra/Spring Health/Modern Health mental-health session-cap planners.
Optional later polish via frontier LLMs must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class MentalHealthSessionCapGapReport:
    """Human-reviewable report."""

    offered_sessions: int
    needed_sessions: int
    coverage_ratio: float
    remaining_cap: float
    coverage_band: str
    guidance: list[str]
    requires_human_review: bool
    auto_approve: bool


class MentalHealthSessionCapGapAdvisor:
    """Advise coverage bands for HITL review."""

    def advise(
        self,
        *,
        offered_sessions: int,
        needed_sessions: int,
    ) -> MentalHealthSessionCapGapReport:
        """Compute coverage band.

        Returns:
            Report with auto_approve=False.

        Raises:
            ValueError: On invalid numeric inputs.
        """

        if offered_sessions < 0:
            raise ValueError("offered_sessions must be >= 0")
        if needed_sessions <= 0:
            raise ValueError("needed_sessions must be > 0")

        coverage_ratio = round(min(offered_sessions, needed_sessions) / float(needed_sessions), 4)
        remaining_cap = float(max(needed_sessions - offered_sessions, 0))

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

        return MentalHealthSessionCapGapReport(
            offered_sessions=int(offered_sessions),
            needed_sessions=int(needed_sessions),
            coverage_ratio=float(coverage_ratio),
            remaining_cap=float(remaining_cap),
            coverage_band=band,
            guidance=guidance,
            requires_human_review=True,
            auto_approve=False,
        )

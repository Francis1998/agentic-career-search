"""HITL ProfessionalDevelopmentStipendGapAdvisor (offline; never auto-acts).

Closes closed-UI planner gaps with coverage bands.
Never auto-acts and never performs network I/O.
Distinct from `LearningStipendGapAdvisor` / `TuitionReimbursementCapGapAdvisor`.
Gap vs Guild/LinkedIn Learning/Workday professional-development stipend planners.
Optional later polish via frontier LLMs must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class ProfessionalDevelopmentStipendGapReport:
    """Human-reviewable report."""

    offered_usd: float
    needed_usd: float
    coverage_ratio: float
    remaining_cap: float
    coverage_band: str
    guidance: list[str]
    requires_human_review: bool
    auto_approve: bool


class ProfessionalDevelopmentStipendGapAdvisor:
    """Advise coverage bands for HITL review."""

    def advise(
        self,
        *,
        offered_usd: float,
        needed_usd: float,
    ) -> ProfessionalDevelopmentStipendGapReport:
        """Compute coverage band.

        Args:
            offered_usd: Observed value (>= 0).
            needed_usd: Target value (> 0).

        Returns:
            Report with auto_approve=False.

        Raises:
            ValueError: On invalid numeric inputs.
        """

        if offered_usd < 0:
            raise ValueError("offered_usd must be >= 0")
        if needed_usd <= 0:
            raise ValueError("needed_usd must be > 0")

        coverage_ratio = round(min(offered_usd, needed_usd) / needed_usd, 4)
        remaining_cap = round(max(needed_usd - offered_usd, 0.0), 2)

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

        return ProfessionalDevelopmentStipendGapReport(
            offered_usd=float(offered_usd),
            needed_usd=float(needed_usd),
            coverage_ratio=float(coverage_ratio),
            remaining_cap=float(remaining_cap),
            coverage_band=band,
            guidance=guidance,
            requires_human_review=True,
            auto_approve=False,
        )

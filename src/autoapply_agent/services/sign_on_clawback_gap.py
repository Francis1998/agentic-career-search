"""HITL SignOnClawbackGapAdvisor (offline; never auto-acts).

Closes closed-UI planner gaps with coverage bands.
Never auto-acts and never performs network I/O.
Distinct from `RetentionBonusCliffAdvisor` / `RelocationRepayment` style cash planners.
Optional later polish via frontier LLMs must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class SignOnClawbackGapReport:
    """Human-reviewable report."""

    clawback_months: float
    needed_months: float
    coverage_ratio: float
    remaining_cap: float
    coverage_band: str
    guidance: list[str]
    requires_human_review: bool
    auto_enroll: bool


class SignOnClawbackGapAdvisor:
    """Advise coverage bands for HITL review."""

    def advise(
        self,
        *,
        clawback_months: float,
        needed_months: float,
    ) -> SignOnClawbackGapReport:
        """Compute coverage band.

        Args:
            clawback_months: Observed value (>= 0).
            needed_months: Target value (> 0).

        Returns:
            SignOnClawbackGapReport with auto_enroll=False.

        Raises:
            ValueError: On invalid numeric inputs.
        """

        if clawback_months < 0:
            raise ValueError("clawback_months must be >= 0")
        if needed_months <= 0:
            raise ValueError("needed_months must be > 0")

        coverage_ratio = round(min(clawback_months, needed_months) / needed_months, 4)
        remaining_cap = round(max(needed_months - clawback_months, 0.0), 2)

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

        return SignOnClawbackGapReport(
            clawback_months=float(clawback_months),
            needed_months=float(needed_months),
            coverage_ratio=float(coverage_ratio),
            remaining_cap=float(remaining_cap),
            coverage_band=band,
            guidance=guidance,
            requires_human_review=True,
            auto_enroll=False,
        )

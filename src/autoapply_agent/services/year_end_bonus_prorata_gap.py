"""HITL YearEndBonusProrataGapAdvisor (offline; never auto-acts).

Closes closed-UI planner gaps with coverage bands.
Never auto-acts and never performs network I/O.
Distinct from `PerformanceBonusTargetGapAdvisor` / `RetentionBonusCliffAdvisor`.
Optional later polish via frontier LLMs must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class YearEndBonusProrataGapReport:
    """Human-reviewable report."""

    prorata_pct: float
    target_pct: float
    coverage_ratio: float
    remaining_cap: float
    coverage_band: str
    guidance: list[str]
    requires_human_review: bool
    auto_enroll: bool


class YearEndBonusProrataGapAdvisor:
    """Advise coverage bands for HITL review."""

    def advise(
        self,
        *,
        prorata_pct: float,
        target_pct: float,
    ) -> YearEndBonusProrataGapReport:
        """Compute coverage band.

        Args:
            prorata_pct: Observed value (>= 0).
            target_pct: Target value (> 0).

        Returns:
            YearEndBonusProrataGapReport with auto_enroll=False.

        Raises:
            ValueError: On invalid numeric inputs.
        """

        if prorata_pct < 0:
            raise ValueError("prorata_pct must be >= 0")
        if target_pct <= 0:
            raise ValueError("target_pct must be > 0")

        coverage_ratio = round(min(prorata_pct, target_pct) / target_pct, 4)
        remaining_cap = round(max(target_pct - prorata_pct, 0.0), 2)

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

        return YearEndBonusProrataGapReport(
            prorata_pct=float(prorata_pct),
            target_pct=float(target_pct),
            coverage_ratio=float(coverage_ratio),
            remaining_cap=float(remaining_cap),
            coverage_band=band,
            guidance=guidance,
            requires_human_review=True,
            auto_enroll=False,
        )

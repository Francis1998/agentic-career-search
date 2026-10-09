"""HITL RetentionBonusCliffAdvisor (offline; never auto-acts).

Closes closed-UI planner gaps with coverage bands.
Never auto-acts and never performs network I/O.
Distinct from `SigningBonusClawbackAdvisor` and `ChangeOfControlAccelerationAdvisor`.
Optional later polish via frontier LLMs must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class RetentionBonusCliffReport:
    """Human-reviewable report."""

    months_to_cliff: float
    target_buffer_months: float
    coverage_ratio: float
    remaining_cap: float
    coverage_band: str
    guidance: list[str]
    requires_human_review: bool
    auto_enroll: bool


class RetentionBonusCliffAdvisor:
    """Advise coverage bands for HITL review."""

    def advise(
        self,
        *,
        months_to_cliff: float,
        target_buffer_months: float,
    ) -> RetentionBonusCliffReport:
        """Compute coverage band.

        Args:
            months_to_cliff: Observed metric (``> 0``).
            target_buffer_months: Target value (``> 0``).

        Returns:
            RetentionBonusCliffReport with ``auto_enroll=False``.

        Raises:
            ValueError: On invalid numeric inputs.
        """

        if months_to_cliff <= 0:
            raise ValueError("months_to_cliff must be > 0")
        if target_buffer_months <= 0:
            raise ValueError("target_buffer_months must be > 0")

        coverage_ratio = round(
            min(months_to_cliff, target_buffer_months) / target_buffer_months,
            4,
        )
        remaining_cap = round(max(months_to_cliff - target_buffer_months, 0.0), 2)

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

        return RetentionBonusCliffReport(
            months_to_cliff=float(months_to_cliff),
            target_buffer_months=float(target_buffer_months),
            coverage_ratio=float(coverage_ratio),
            remaining_cap=float(remaining_cap),
            coverage_band=band,
            guidance=guidance,
            requires_human_review=True,
            auto_enroll=False,
        )

"""HITL ChangeOfControlAccelerationAdvisor (offline; never auto-acts).

Closes closed-UI planner gaps with coverage bands.
Never auto-acts and never performs network I/O.
Distinct from `EquityVestingCliffAdvisor` and `SigningBonusClawbackAdvisor`.
Optional later polish via frontier LLMs must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class ChangeOfControlAccelerationReport:
    """Human-reviewable report."""

    accelerated_pct: float
    target_accelerated_pct: float
    coverage_ratio: float
    remaining_cap: float
    coverage_band: str
    guidance: list[str]
    requires_human_review: bool
    auto_enroll: bool


class ChangeOfControlAccelerationAdvisor:
    """Advise coverage bands for HITL review."""

    def advise(
        self,
        *,
        accelerated_pct: float,
        target_accelerated_pct: float,
    ) -> ChangeOfControlAccelerationReport:
        """Compute coverage band.

        Args:
            accelerated_pct: Observed available quantity (``> 0``).
            target_accelerated_pct: Required quantity (``> 0``).

        Returns:
            ChangeOfControlAccelerationReport with ``auto_enroll=False``.

        Raises:
            ValueError: On invalid numeric inputs.
        """

        if accelerated_pct <= 0:
            raise ValueError("accelerated_pct must be > 0")
        if target_accelerated_pct <= 0:
            raise ValueError("target_accelerated_pct must be > 0")

        coverage_ratio = round(
            min(accelerated_pct, target_accelerated_pct) / target_accelerated_pct,
            4,
        )
        remaining_cap = round(max(accelerated_pct - target_accelerated_pct, 0.0), 2)

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

        return ChangeOfControlAccelerationReport(
            accelerated_pct=float(accelerated_pct),
            target_accelerated_pct=float(target_accelerated_pct),
            coverage_ratio=float(coverage_ratio),
            remaining_cap=float(remaining_cap),
            coverage_band=band,
            guidance=guidance,
            requires_human_review=True,
            auto_enroll=False,
        )

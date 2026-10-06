"""HITL SideProjectIpAssignmentAdvisor (offline; never auto-acts).

Closes closed-UI planner gaps with coverage bands.
Never auto-acts and never performs network I/O.
Distinct from `StockOptionExerciseWindowAdvisor` and `ChangeOfControlAccelerationAdvisor`.
Optional later polish via frontier LLMs must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class SideProjectIpAssignmentReport:
    """Human-reviewable report."""

    retained_ip_pct: float
    target_retain_pct: float
    coverage_ratio: float
    remaining_cap: float
    coverage_band: str
    guidance: list[str]
    requires_human_review: bool
    auto_enroll: bool


class SideProjectIpAssignmentAdvisor:
    """Advise coverage bands for HITL review."""

    def advise(
        self,
        *,
        retained_ip_pct: float,
        target_retain_pct: float,
    ) -> SideProjectIpAssignmentReport:
        """Compute coverage band.

        Args:
            retained_ip_pct: Observed retained IP percent (``> 0``).
            target_retain_pct: Target retain percent (``> 0``).

        Returns:
            SideProjectIpAssignmentReport with ``auto_enroll=False``.

        Raises:
            ValueError: On invalid numeric inputs.
        """

        if retained_ip_pct <= 0:
            raise ValueError("retained_ip_pct must be > 0")
        if target_retain_pct <= 0:
            raise ValueError("target_retain_pct must be > 0")

        coverage_ratio = round(
            min(retained_ip_pct, target_retain_pct) / target_retain_pct,
            4,
        )
        remaining_cap = round(max(retained_ip_pct - target_retain_pct, 0.0), 2)

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

        return SideProjectIpAssignmentReport(
            retained_ip_pct=float(retained_ip_pct),
            target_retain_pct=float(target_retain_pct),
            coverage_ratio=float(coverage_ratio),
            remaining_cap=float(remaining_cap),
            coverage_band=band,
            guidance=guidance,
            requires_human_review=True,
            auto_enroll=False,
        )

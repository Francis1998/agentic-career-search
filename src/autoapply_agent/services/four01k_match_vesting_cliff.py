"""HITL Four01kMatchVestingCliffAdvisor (offline; never auto-acts).

Closes closed-UI planner gaps with coverage bands.
Never auto-acts and never performs network I/O.
Distinct from `Four01kMatchGapAdvisor` and `EquityVestingAdvisor`.
Optional later polish via frontier LLMs must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class Four01kMatchVestingCliffReport:
    """Human-reviewable report."""

    vested_match_pct: float
    target_vested_pct: float
    coverage_ratio: float
    remaining_cap: float
    coverage_band: str
    guidance: list[str]
    requires_human_review: bool
    auto_enroll: bool


class Four01kMatchVestingCliffAdvisor:
    """Advise coverage bands for HITL review."""

    def advise(
        self,
        *,
        vested_match_pct: float,
        target_vested_pct: float,
    ) -> Four01kMatchVestingCliffReport:
        """Compute coverage band.

        Args:
            vested_match_pct: Observed metric (``> 0``).
            target_vested_pct: Target value (``> 0``).

        Returns:
            Four01kMatchVestingCliffReport with ``auto_enroll=False``.

        Raises:
            ValueError: On invalid numeric inputs.
        """

        if vested_match_pct <= 0:
            raise ValueError("vested_match_pct must be > 0")
        if target_vested_pct <= 0:
            raise ValueError("target_vested_pct must be > 0")

        coverage_ratio = round(
            min(vested_match_pct, target_vested_pct) / target_vested_pct,
            4,
        )
        remaining_cap = round(max(vested_match_pct - target_vested_pct, 0.0), 2)

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

        return Four01kMatchVestingCliffReport(
            vested_match_pct=float(vested_match_pct),
            target_vested_pct=float(target_vested_pct),
            coverage_ratio=float(coverage_ratio),
            remaining_cap=float(remaining_cap),
            coverage_band=band,
            guidance=guidance,
            requires_human_review=True,
            auto_enroll=False,
        )

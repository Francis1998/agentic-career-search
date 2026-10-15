"""HITL Four01kMatchTrueUpGapAdvisor (offline; never auto-acts).

Closes closed-UI planner gaps with coverage bands.
Never auto-acts and never performs network I/O.
Distinct from `FourOhOneKMatchGapAdvisor` / `Four01kMatchVestingCliffAdvisor`.
Optional later polish via frontier LLMs must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class Four01kMatchTrueUpGapReport:
    """Human-reviewable report."""

    true_up_credited_usd: float
    true_up_owed_usd: float
    coverage_ratio: float
    remaining_cap: float
    coverage_band: str
    guidance: list[str]
    requires_human_review: bool
    auto_enroll: bool


class Four01kMatchTrueUpGapAdvisor:
    """Advise coverage bands for HITL review."""

    def advise(
        self,
        *,
        true_up_credited_usd: float,
        true_up_owed_usd: float,
    ) -> Four01kMatchTrueUpGapReport:
        """Compute coverage band.

        Args:
            true_up_credited_usd: Observed value (>= 0).
            true_up_owed_usd: Target value (> 0).

        Returns:
            Four01kMatchTrueUpGapReport with auto_enroll=False.

        Raises:
            ValueError: On invalid numeric inputs.
        """

        if true_up_credited_usd < 0:
            raise ValueError("true_up_credited_usd must be >= 0")
        if true_up_owed_usd <= 0:
            raise ValueError("true_up_owed_usd must be > 0")

        coverage_ratio = round(min(true_up_credited_usd, true_up_owed_usd) / true_up_owed_usd, 4)
        remaining_cap = round(max(true_up_owed_usd - true_up_credited_usd, 0.0), 2)

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

        return Four01kMatchTrueUpGapReport(
            true_up_credited_usd=float(true_up_credited_usd),
            true_up_owed_usd=float(true_up_owed_usd),
            coverage_ratio=float(coverage_ratio),
            remaining_cap=float(remaining_cap),
            coverage_band=band,
            guidance=guidance,
            requires_human_review=True,
            auto_enroll=False,
        )

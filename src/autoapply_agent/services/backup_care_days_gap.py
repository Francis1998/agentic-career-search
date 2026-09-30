"""HITL BackupCareDaysGapAdvisor (offline; never auto-acts).

Closes the gap vs Bright Horizons/Care.com/Levels.fyi backup-care day planners
locked in closed UIs. Emits coverage bands — never auto-acts and never
performs network I/O.

Distinct from ``DependentCareFsaGapAdvisor`` and
``ParentalLeaveGapAdvisor``. Optional later polish via
GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class BackupCareDaysGapReport:
    """Human-reviewable coverage report."""

    needed_backup_days: float
    employer_backup_days: float
    planned_use_days: float
    coverage_ratio: float
    remaining_cap_days: float
    coverage_band: str
    guidance: list[str]
    requires_human_review: bool
    auto_claim: bool


class BackupCareDaysGapAdvisor:
    """Advise coverage bands for HITL review."""

    def advise(
        self,
        *,
        needed_backup_days: float,
        employer_backup_days: float,
        planned_use_days: float,
    ) -> BackupCareDaysGapReport:
        """Compute coverage band.

        Args:
            needed_backup_days: Needed backup-care days per year (``> 0``).
            employer_backup_days: Employer-provided backup-care days (``> 0``).
            planned_use_days: Planned use of backup days (``>= 0``).

        Returns:
            BackupCareDaysGapReport with ``auto_claim=False``.

        Raises:
            ValueError: On invalid numeric inputs.
        """

        if needed_backup_days <= 0:
            raise ValueError("needed_backup_days must be > 0")
        if employer_backup_days <= 0:
            raise ValueError("employer_backup_days must be > 0")
        if planned_use_days < 0:
            raise ValueError("planned_use_days must be >= 0")

        covered = min(employer_backup_days, planned_use_days)
        coverage_ratio = round(covered / needed_backup_days, 4)
        remaining_cap = round(max(employer_backup_days - planned_use_days, 0.0), 2)

        if coverage_ratio >= 0.9:
            band = "well_covered"
        elif coverage_ratio >= 0.5:
            band = "partial_gap"
        else:
            band = "under_covered"

        guidance = [
            "Backup-care day math is advisory; verify vendor eligibility windows.",
            "Do not auto-book backup care from this advisor.",
        ]
        if band == "well_covered":
            guidance.append("Employer days cover most need; confirm booking lead times.")
        elif band == "partial_gap":
            guidance.append("Partial day coverage; plan PTO bridge for school closures.")
        else:
            guidance.append("Days thin vs need; negotiate more days or DCFSA bridge.")

        return BackupCareDaysGapReport(
            needed_backup_days=float(needed_backup_days),
            employer_backup_days=float(employer_backup_days),
            planned_use_days=float(planned_use_days),
            coverage_ratio=float(coverage_ratio),
            remaining_cap_days=float(remaining_cap),
            coverage_band=band,
            guidance=guidance,
            requires_human_review=True,
            auto_claim=False,
        )

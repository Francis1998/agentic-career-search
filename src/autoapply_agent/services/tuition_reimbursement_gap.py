"""HITL tuition reimbursement gap advisor (offline; never auto-claims).

Closes the gap vs Levels.fyi / Blind / Candor tuition / learning-budget
planners locked in closed UIs. Given annual tuition cost, employer
reimbursement cap, and expected claim USD, emits coverage bands —
never auto-claims and never performs network I/O.

Distinct from ``SkillGapLearningAdvisor`` (skill gaps) and
``HomeOfficeStipendGapAdvisor`` (home-office stipend). Optional later polish via
GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class TuitionReimbursementGapReport:
    """Human-reviewable tuition reimbursement coverage report."""

    annual_tuition_usd: float
    employer_cap_usd: float
    planned_claim_usd: float
    coverage_ratio: float
    remaining_cap_usd: float
    coverage_band: str
    guidance: list[str]
    requires_human_review: bool
    auto_claim: bool


class TuitionReimbursementGapAdvisor:
    """Advise tuition reimbursement coverage vs employer annual cap."""

    def advise(
        self,
        *,
        annual_tuition_usd: float,
        employer_cap_usd: float,
        planned_claim_usd: float,
    ) -> TuitionReimbursementGapReport:
        """Compute tuition reimbursement coverage band.

        Args:
            annual_tuition_usd: Expected annual tuition cost (``> 0``).
            employer_cap_usd: Employer annual reimbursement cap (``> 0``).
            planned_claim_usd: Planned claim against the cap (``>= 0``).

        Returns:
            TuitionReimbursementGapReport with ``auto_claim=False``.

        Raises:
            ValueError: On invalid numeric inputs.
        """

        if annual_tuition_usd <= 0:
            raise ValueError("annual_tuition_usd must be > 0")
        if employer_cap_usd <= 0:
            raise ValueError("employer_cap_usd must be > 0")
        if planned_claim_usd < 0:
            raise ValueError("planned_claim_usd must be >= 0")

        coverage_ratio = round(min(employer_cap_usd, planned_claim_usd) / annual_tuition_usd, 4)
        remaining_cap = round(max(employer_cap_usd - planned_claim_usd, 0.0), 2)

        if coverage_ratio >= 0.9:
            band = "well_covered"
        elif coverage_ratio >= 0.5:
            band = "partial_gap"
        else:
            band = "under_covered"

        guidance = [
            "Tuition reimbursement math is advisory; verify policy grades, caps, and taxes.",
            "Do not auto-claim tuition reimbursement from this advisor.",
        ]
        if band == "well_covered":
            guidance.append(
                "Cap covers most tuition; confirm paperwork deadlines and grade requirements."
            )
        elif band == "partial_gap":
            guidance.append("Partial coverage; budget out-of-pocket remainder before enrollment.")
        else:
            guidance.append("Cap thin vs tuition; negotiate learning budget or phase coursework.")

        return TuitionReimbursementGapReport(
            annual_tuition_usd=float(annual_tuition_usd),
            employer_cap_usd=float(employer_cap_usd),
            planned_claim_usd=float(planned_claim_usd),
            coverage_ratio=float(coverage_ratio),
            remaining_cap_usd=float(remaining_cap),
            coverage_band=band,
            guidance=guidance,
            requires_human_review=True,
            auto_claim=False,
        )

"""HITL student-loan repayment gap advisor (offline; never auto-enrolls).

Closes the gap vs Student Loan Hero / Rippling / Levels.fyi employer
student-loan repayment (SLPRP) planners locked in closed UIs. Given
monthly payment, employer monthly contribution, and months remaining,
emits coverage bands — never auto-enrolls and never performs network I/O.

Distinct from ``TuitionReimbursementGapAdvisor`` (tuition claims) and
``FourOhOneKMatchGapAdvisor`` (401k match). Optional later polish via
GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2 must stay advisory.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class StudentLoanRepaymentGapReport:
    """Human-reviewable student-loan repayment coverage report."""

    monthly_payment_usd: float
    employer_monthly_usd: float
    months_remaining: float
    coverage_ratio: float
    uncovered_monthly_usd: float
    coverage_band: str
    guidance: list[str]
    requires_human_review: bool
    auto_enroll: bool


class StudentLoanRepaymentGapAdvisor:
    """Advise employer student-loan repayment coverage vs payment."""

    def advise(
        self,
        *,
        monthly_payment_usd: float,
        employer_monthly_usd: float,
        months_remaining: float,
    ) -> StudentLoanRepaymentGapReport:
        """Compute student-loan repayment coverage band.

        Args:
            monthly_payment_usd: Borrower monthly payment (``> 0``).
            employer_monthly_usd: Employer monthly SLPRP contribution (``>= 0``).
            months_remaining: Remaining repayment months (``> 0``).

        Returns:
            StudentLoanRepaymentGapReport with ``auto_enroll=False``.

        Raises:
            ValueError: On invalid numeric inputs.
        """

        if monthly_payment_usd <= 0:
            raise ValueError("monthly_payment_usd must be > 0")
        if employer_monthly_usd < 0:
            raise ValueError("employer_monthly_usd must be >= 0")
        if months_remaining <= 0:
            raise ValueError("months_remaining must be > 0")

        coverage_ratio = round(
            min(employer_monthly_usd, monthly_payment_usd) / monthly_payment_usd, 4
        )
        uncovered = round(max(monthly_payment_usd - employer_monthly_usd, 0.0), 2)

        if coverage_ratio >= 0.9:
            band = "well_covered"
        elif coverage_ratio >= 0.4:
            band = "partial_gap"
        else:
            band = "under_covered"

        guidance = [
            "Student-loan repayment math is advisory; verify annual caps and tax treatment.",
            "Do not auto-enroll student-loan repayment from this advisor.",
        ]
        if band == "well_covered":
            guidance.append(
                "Employer contribution covers most of the payment; confirm payroll setup."
            )
        elif band == "partial_gap":
            guidance.append(
                "Partial coverage; budget uncovered monthly amount across remaining term."
            )
        else:
            guidance.append("Contribution thin vs payment; negotiate SLPRP or refinance options.")

        return StudentLoanRepaymentGapReport(
            monthly_payment_usd=float(monthly_payment_usd),
            employer_monthly_usd=float(employer_monthly_usd),
            months_remaining=float(months_remaining),
            coverage_ratio=float(coverage_ratio),
            uncovered_monthly_usd=float(uncovered),
            coverage_band=band,
            guidance=guidance,
            requires_human_review=True,
            auto_enroll=False,
        )

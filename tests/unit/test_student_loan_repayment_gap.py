"""Unit tests for StudentLoanRepaymentGapAdvisor."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from autoapply_agent.services.student_loan_repayment_gap import (
    StudentLoanRepaymentGapAdvisor,
)


def test_well_covered() -> None:
    """High coverage ratio is well_covered."""

    report = StudentLoanRepaymentGapAdvisor().advise(
        monthly_payment_usd=400.0,
        employer_monthly_usd=400.0,
        months_remaining=48.0,
    )
    assert report.coverage_band == "well_covered"
    assert report.auto_enroll is False
    assert report.requires_human_review is True


def test_partial_gap() -> None:
    """Mid coverage is partial_gap."""

    report = StudentLoanRepaymentGapAdvisor().advise(
        monthly_payment_usd=500.0,
        employer_monthly_usd=200.0,
        months_remaining=60.0,
    )
    assert report.coverage_band == "partial_gap"


def test_under_covered() -> None:
    """Low coverage is under_covered."""

    report = StudentLoanRepaymentGapAdvisor().advise(
        monthly_payment_usd=600.0,
        employer_monthly_usd=50.0,
        months_remaining=72.0,
    )
    assert report.coverage_band == "under_covered"


def test_invalid_payment_raises() -> None:
    """Non-positive monthly payment raises ValueError."""

    with pytest.raises(ValueError, match="monthly_payment_usd"):
        StudentLoanRepaymentGapAdvisor().advise(
            monthly_payment_usd=0.0,
            employer_monthly_usd=100.0,
            months_remaining=12.0,
        )


def test_no_network_calls() -> None:
    """Advisor never performs HTTP calls."""

    with (
        patch("httpx.Client", MagicMock()) as client_cls,
        patch("httpx.AsyncClient", MagicMock()) as async_cls,
        patch("httpx.get", MagicMock()) as get_fn,
        patch("httpx.post", MagicMock()) as post_fn,
    ):
        StudentLoanRepaymentGapAdvisor().advise(
            monthly_payment_usd=350.0,
            employer_monthly_usd=100.0,
            months_remaining=36.0,
        )
        client_cls.assert_not_called()
        async_cls.assert_not_called()
        get_fn.assert_not_called()
        post_fn.assert_not_called()

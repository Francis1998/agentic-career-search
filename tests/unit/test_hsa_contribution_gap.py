"""Unit tests for HsaContributionGapAdvisor."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from autoapply_agent.services.hsa_contribution_gap import HsaContributionGapAdvisor


def test_fully_funded() -> None:
    """Employee + employer meeting IRS limit is fully_funded."""

    report = HsaContributionGapAdvisor().advise(
        employee_ytd_usd=3000.0,
        employer_ytd_usd=1500.0,
        irs_limit_usd=4300.0,
    )
    assert report.coverage_band == "fully_funded"
    assert report.auto_enroll is False
    assert report.requires_human_review is True


def test_partial_gap() -> None:
    """Contribution between 60% and 100% of limit is partial_gap."""

    report = HsaContributionGapAdvisor().advise(
        employee_ytd_usd=2500.0,
        employer_ytd_usd=500.0,
        irs_limit_usd=4300.0,
    )
    assert report.coverage_band == "partial_gap"
    assert report.remaining_room_usd == 1300.0


def test_under_contributing() -> None:
    """Below 60% of IRS limit is under_contributing."""

    report = HsaContributionGapAdvisor().advise(
        employee_ytd_usd=500.0,
        employer_ytd_usd=0.0,
        irs_limit_usd=4300.0,
    )
    assert report.coverage_band == "under_contributing"


def test_invalid_limit_raises() -> None:
    """Non-positive IRS limit raises ValueError."""

    with pytest.raises(ValueError, match="irs_limit_usd"):
        HsaContributionGapAdvisor().advise(
            employee_ytd_usd=100.0,
            employer_ytd_usd=0.0,
            irs_limit_usd=0.0,
        )


def test_no_network_calls() -> None:
    """Advisor never performs HTTP calls."""

    with (
        patch("httpx.Client", MagicMock()) as client_cls,
        patch("httpx.AsyncClient", MagicMock()) as async_cls,
        patch("httpx.get", MagicMock()) as get_fn,
        patch("httpx.post", MagicMock()) as post_fn,
    ):
        HsaContributionGapAdvisor().advise(
            employee_ytd_usd=1000.0,
            employer_ytd_usd=500.0,
            irs_limit_usd=4300.0,
        )
        client_cls.assert_not_called()
        async_cls.assert_not_called()
        get_fn.assert_not_called()
        post_fn.assert_not_called()

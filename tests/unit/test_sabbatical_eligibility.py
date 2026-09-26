"""Unit tests for SabbaticalEligibilityAdvisor."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from autoapply_agent.services.sabbatical_eligibility import SabbaticalEligibilityAdvisor


def test_eligible() -> None:
    """Tenure meeting policy years is eligible."""

    report = SabbaticalEligibilityAdvisor().advise(
        tenure_years=7.0,
        policy_years=5.0,
        sabbatical_weeks_offered=6,
        market_weeks=6,
    )
    assert report.eligibility_band == "eligible"
    assert report.auto_approve is False
    assert report.requires_human_review is True


def test_near_eligible() -> None:
    """Tenure within 80% of policy is near_eligible."""

    report = SabbaticalEligibilityAdvisor().advise(
        tenure_years=4.2,
        policy_years=5.0,
        sabbatical_weeks_offered=4,
        market_weeks=6,
    )
    assert report.eligibility_band == "near_eligible"


def test_ineligible_thin() -> None:
    """Low tenure with thin weeks is ineligible_thin."""

    report = SabbaticalEligibilityAdvisor().advise(
        tenure_years=1.0,
        policy_years=5.0,
        sabbatical_weeks_offered=2,
        market_weeks=8,
    )
    assert report.eligibility_band == "ineligible_thin"


def test_invalid_policy_raises() -> None:
    """Non-positive policy years raises ValueError."""

    with pytest.raises(ValueError, match="policy_years"):
        SabbaticalEligibilityAdvisor().advise(
            tenure_years=3.0,
            policy_years=0.0,
            sabbatical_weeks_offered=4,
            market_weeks=6,
        )


def test_no_network_calls() -> None:
    """Advisor never performs HTTP calls."""

    with (
        patch("httpx.Client", MagicMock()) as client_cls,
        patch("httpx.AsyncClient", MagicMock()) as async_cls,
        patch("httpx.get", MagicMock()) as get_fn,
        patch("httpx.post", MagicMock()) as post_fn,
    ):
        SabbaticalEligibilityAdvisor().advise(
            tenure_years=3.0,
            policy_years=5.0,
            sabbatical_weeks_offered=4,
            market_weeks=6,
        )
        client_cls.assert_not_called()
        async_cls.assert_not_called()
        get_fn.assert_not_called()
        post_fn.assert_not_called()

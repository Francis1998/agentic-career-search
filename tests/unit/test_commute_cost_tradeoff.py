"""Unit tests for CommuteCostTradeoffAdvisor."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from autoapply_agent.services.commute_cost_tradeoff import CommuteCostTradeoffAdvisor


def test_favor_remote_when_commute_exceeds_stipend() -> None:
    """Heavy commute with thin stipend favors remote."""

    report = CommuteCostTradeoffAdvisor().advise(
        commute_minutes_one_way=60.0,
        office_days_per_week=5.0,
        hourly_time_value=50.0,
        weekly_transit_cost=100.0,
        remote_stipend_monthly=50.0,
    )
    assert report.tradeoff_band == "favor_remote"
    assert report.auto_accept is False
    assert report.annual_commute_cost_usd > report.annual_stipend_usd


def test_favor_office_when_commute_is_light() -> None:
    """Light commute with covering stipend favors office dollars."""

    report = CommuteCostTradeoffAdvisor().advise(
        commute_minutes_one_way=5.0,
        office_days_per_week=1.0,
        hourly_time_value=20.0,
        weekly_transit_cost=0.0,
        remote_stipend_monthly=100.0,
    )
    assert report.tradeoff_band == "favor_office"


def test_mixed_mid_burden() -> None:
    """Moderate uncovered burden lands in mixed."""

    report = CommuteCostTradeoffAdvisor().advise(
        commute_minutes_one_way=20.0,
        office_days_per_week=2.0,
        hourly_time_value=30.0,
        weekly_transit_cost=10.0,
        remote_stipend_monthly=40.0,
    )
    assert report.tradeoff_band in {"mixed", "favor_remote", "favor_office"}
    assert report.requires_human_review is True


def test_invalid_days_raises() -> None:
    """Office days outside 0..7 raises ValueError."""

    with pytest.raises(ValueError, match="office_days_per_week"):
        CommuteCostTradeoffAdvisor().advise(
            commute_minutes_one_way=20.0,
            office_days_per_week=8.0,
            hourly_time_value=30.0,
        )


def test_no_network_calls() -> None:
    """Advisor never performs HTTP calls."""

    with (
        patch("httpx.Client", MagicMock()) as client_cls,
        patch("httpx.AsyncClient", MagicMock()) as async_cls,
        patch("httpx.get", MagicMock()) as get_fn,
        patch("httpx.post", MagicMock()) as post_fn,
    ):
        CommuteCostTradeoffAdvisor().advise(
            commute_minutes_one_way=30.0,
            office_days_per_week=3.0,
            hourly_time_value=45.0,
            remote_stipend_monthly=200.0,
        )
        client_cls.assert_not_called()
        async_cls.assert_not_called()
        get_fn.assert_not_called()
        post_fn.assert_not_called()

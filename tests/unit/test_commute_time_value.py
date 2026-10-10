"""Unit tests for CommuteTimeValueAdvisor."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from autoapply_agent.services.commute_time_value import CommuteTimeValueAdvisor


def test_well_covered() -> None:
    """Band well_covered."""

    report = CommuteTimeValueAdvisor().advise(
        weekly_commute_hours=5.0,
        hourly_opportunity_cost=30.0,
    )
    assert report.coverage_band == "well_covered"
    assert report.weekly_time_value == 150.0
    assert report.auto_enroll is False
    assert report.requires_human_review is True


def test_partial_gap() -> None:
    """Band partial_gap."""

    report = CommuteTimeValueAdvisor().advise(
        weekly_commute_hours=10.0,
        hourly_opportunity_cost=30.0,
    )
    assert report.coverage_band == "partial_gap"


def test_under_covered() -> None:
    """Band under_covered."""

    report = CommuteTimeValueAdvisor().advise(
        weekly_commute_hours=20.0,
        hourly_opportunity_cost=40.0,
    )
    assert report.coverage_band == "under_covered"


def test_invalid_raises() -> None:
    """Invalid numeric input raises ValueError."""

    with pytest.raises(ValueError, match="hourly_opportunity_cost"):
        CommuteTimeValueAdvisor().advise(
            weekly_commute_hours=5.0,
            hourly_opportunity_cost=0.0,
        )


def test_no_network_calls() -> None:
    """Advisor never performs HTTP calls."""

    with (
        patch("httpx.Client", MagicMock()) as client_cls,
        patch("httpx.AsyncClient", MagicMock()) as async_cls,
        patch("httpx.get", MagicMock()) as get_fn,
        patch("httpx.post", MagicMock()) as post_fn,
    ):
        CommuteTimeValueAdvisor().advise(
            weekly_commute_hours=8.0,
            hourly_opportunity_cost=35.0,
        )
        client_cls.assert_not_called()
        async_cls.assert_not_called()
        get_fn.assert_not_called()
        post_fn.assert_not_called()

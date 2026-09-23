"""Unit tests for ParentalLeaveGapAdvisor."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from autoapply_agent.services.parental_leave_gap import ParentalLeaveGapAdvisor


def test_at_or_above_market() -> None:
    """Offered weeks at market are at_or_above_market."""

    report = ParentalLeaveGapAdvisor().advise(offered_weeks=12.0, market_weeks=12.0)
    assert report.coverage_band == "at_or_above_market"
    assert report.coverage_ratio == 1.0
    assert report.auto_accept is False


def test_thin_leave() -> None:
    """Less than half market is thin."""

    report = ParentalLeaveGapAdvisor().advise(offered_weeks=4.0, market_weeks=12.0)
    assert report.coverage_band == "thin"


def test_below_market_band() -> None:
    """Between 0.5 and 0.75 is below_market."""

    report = ParentalLeaveGapAdvisor().advise(offered_weeks=7.0, market_weeks=12.0)
    assert report.coverage_band == "below_market"


def test_invalid_market_raises() -> None:
    """Non-positive market_weeks raises ValueError."""

    with pytest.raises(ValueError, match="market_weeks"):
        ParentalLeaveGapAdvisor().advise(offered_weeks=1.0, market_weeks=0)


def test_no_network_calls() -> None:
    """Advisor never performs HTTP calls."""

    with (
        patch("httpx.Client", MagicMock()) as client_cls,
        patch("httpx.AsyncClient", MagicMock()) as async_cls,
        patch("httpx.get", MagicMock()) as get_fn,
        patch("httpx.post", MagicMock()) as post_fn,
    ):
        ParentalLeaveGapAdvisor().advise(offered_weeks=8.0, market_weeks=12.0)
        client_cls.assert_not_called()
        async_cls.assert_not_called()
        get_fn.assert_not_called()
        post_fn.assert_not_called()

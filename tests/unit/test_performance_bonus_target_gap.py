"""Unit tests for PerformanceBonusTargetGapAdvisor."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from autoapply_agent.services.performance_bonus_target_gap import (
    PerformanceBonusTargetGapAdvisor,
)


def test_at_or_above_market() -> None:
    """Offered >= market is at_or_above_market."""

    report = PerformanceBonusTargetGapAdvisor().advise(
        offered_target_pct=15.0,
        market_target_pct=12.0,
    )
    assert report.gap_band == "at_or_above_market"
    assert report.auto_accept is False


def test_slight_gap() -> None:
    """Shortfall <= 20% of market is slight_gap."""

    report = PerformanceBonusTargetGapAdvisor().advise(
        offered_target_pct=10.0,
        market_target_pct=12.0,
    )
    assert report.gap_band == "slight_gap"


def test_material_gap() -> None:
    """Shortfall > 20% of market is material_gap."""

    report = PerformanceBonusTargetGapAdvisor().advise(
        offered_target_pct=5.0,
        market_target_pct=15.0,
    )
    assert report.gap_band == "material_gap"
    assert report.requires_human_review is True


def test_invalid_market_raises() -> None:
    """Non-positive market target raises ValueError."""

    with pytest.raises(ValueError, match="market_target_pct"):
        PerformanceBonusTargetGapAdvisor().advise(
            offered_target_pct=10.0,
            market_target_pct=0.0,
        )


def test_no_network_calls() -> None:
    """Advisor never performs HTTP calls."""

    with (
        patch("httpx.Client", MagicMock()) as client_cls,
        patch("httpx.AsyncClient", MagicMock()) as async_cls,
        patch("httpx.get", MagicMock()) as get_fn,
        patch("httpx.post", MagicMock()) as post_fn,
    ):
        PerformanceBonusTargetGapAdvisor().advise(
            offered_target_pct=10.0,
            market_target_pct=12.0,
        )
        client_cls.assert_not_called()
        async_cls.assert_not_called()
        get_fn.assert_not_called()
        post_fn.assert_not_called()

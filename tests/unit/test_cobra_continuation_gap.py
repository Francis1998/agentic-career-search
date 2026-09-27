"""Unit tests for CobraContinuationGapAdvisor."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from autoapply_agent.services.cobra_continuation_gap import CobraContinuationGapAdvisor


def test_fully_bridged() -> None:
    """Bridge months covering need is fully_bridged."""

    report = CobraContinuationGapAdvisor().advise(
        monthly_premium_usd=700.0,
        months_needed=6,
        bridge_months_funded=6.0,
    )
    assert report.coverage_band == "fully_bridged"
    assert report.auto_enroll is False
    assert report.requires_human_review is True


def test_partial_gap() -> None:
    """Coverage between 60% and 100% is partial_gap."""

    report = CobraContinuationGapAdvisor().advise(
        monthly_premium_usd=700.0,
        months_needed=10,
        bridge_months_funded=7.0,
    )
    assert report.coverage_band == "partial_gap"
    assert report.coverage_ratio == 0.7


def test_under_bridged() -> None:
    """Below 60% coverage is under_bridged."""

    report = CobraContinuationGapAdvisor().advise(
        monthly_premium_usd=800.0,
        months_needed=12,
        bridge_months_funded=3.0,
    )
    assert report.coverage_band == "under_bridged"


def test_invalid_premium_raises() -> None:
    """Non-positive premium raises ValueError."""

    with pytest.raises(ValueError, match="monthly_premium_usd"):
        CobraContinuationGapAdvisor().advise(
            monthly_premium_usd=0.0,
            months_needed=3,
            bridge_months_funded=1.0,
        )


def test_no_network_calls() -> None:
    """Advisor never performs HTTP calls."""

    with (
        patch("httpx.Client", MagicMock()) as client_cls,
        patch("httpx.AsyncClient", MagicMock()) as async_cls,
        patch("httpx.get", MagicMock()) as get_fn,
        patch("httpx.post", MagicMock()) as post_fn,
    ):
        CobraContinuationGapAdvisor().advise(
            monthly_premium_usd=500.0,
            months_needed=3,
            bridge_months_funded=2.0,
        )
        client_cls.assert_not_called()
        async_cls.assert_not_called()
        get_fn.assert_not_called()
        post_fn.assert_not_called()

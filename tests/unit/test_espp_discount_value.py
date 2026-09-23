"""Unit tests for EsppDiscountValueAdvisor."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from autoapply_agent.services.espp_discount_value import EsppDiscountValueAdvisor


def test_high_value() -> None:
    """Large contribution with 15% discount is high."""

    report = EsppDiscountValueAdvisor().advise(
        contribution_usd=20_000.0,
        discount_pct=15.0,
    )
    assert report.value_band == "high"
    assert report.estimated_value_usd == 3_000.0
    assert report.auto_enroll is False


def test_moderate_value() -> None:
    """Mid contribution lands in moderate."""

    report = EsppDiscountValueAdvisor().advise(
        contribution_usd=6_000.0,
        discount_pct=15.0,
    )
    assert report.value_band == "moderate"
    assert report.estimated_value_usd == 900.0


def test_lookback_uplift() -> None:
    """Lookback uplift increases estimated value."""

    report = EsppDiscountValueAdvisor().advise(
        contribution_usd=10_000.0,
        discount_pct=15.0,
        lookback_uplift_pct=5.0,
    )
    assert report.estimated_value_usd == 2_000.0
    assert report.value_band == "high"


def test_invalid_discount_raises() -> None:
    """Out-of-range discount_pct raises ValueError."""

    with pytest.raises(ValueError, match="discount_pct"):
        EsppDiscountValueAdvisor().advise(
            contribution_usd=100.0,
            discount_pct=150.0,
        )


def test_no_network_calls() -> None:
    """Advisor never performs HTTP calls."""

    with (
        patch("httpx.Client", MagicMock()) as client_cls,
        patch("httpx.AsyncClient", MagicMock()) as async_cls,
        patch("httpx.get", MagicMock()) as get_fn,
        patch("httpx.post", MagicMock()) as post_fn,
    ):
        EsppDiscountValueAdvisor().advise(contribution_usd=1_000.0)
        client_cls.assert_not_called()
        async_cls.assert_not_called()
        get_fn.assert_not_called()
        post_fn.assert_not_called()

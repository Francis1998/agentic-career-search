"""Unit tests for PtoCashOutValueAdvisor."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from autoapply_agent.services.pto_cash_out_value import PtoCashOutValueAdvisor


def test_rich_band_two_weeks() -> None:
    """>=80 hours at rate is rich."""

    report = PtoCashOutValueAdvisor().advise(
        unused_pto_hours=80.0,
        hourly_rate=50.0,
    )
    assert report.value_band == "rich"
    assert report.cash_out_usd == 4_000.0
    assert report.auto_cash is False


def test_fair_band_one_week() -> None:
    """40-80 hours is fair."""

    report = PtoCashOutValueAdvisor().advise(
        unused_pto_hours=40.0,
        hourly_rate=50.0,
    )
    assert report.value_band == "fair"
    assert report.cash_out_usd == 2_000.0


def test_thin_band() -> None:
    """Under one week is thin."""

    report = PtoCashOutValueAdvisor().advise(
        unused_pto_hours=8.0,
        hourly_rate=50.0,
    )
    assert report.value_band == "thin"


def test_invalid_rate_raises() -> None:
    """Non-positive hourly_rate raises ValueError."""

    with pytest.raises(ValueError, match="hourly_rate"):
        PtoCashOutValueAdvisor().advise(
            unused_pto_hours=10.0,
            hourly_rate=0.0,
        )


def test_no_network_calls() -> None:
    """Advisor never performs HTTP calls."""

    with (
        patch("httpx.Client", MagicMock()) as client_cls,
        patch("httpx.AsyncClient", MagicMock()) as async_cls,
        patch("httpx.get", MagicMock()) as get_fn,
        patch("httpx.post", MagicMock()) as post_fn,
    ):
        PtoCashOutValueAdvisor().advise(
            unused_pto_hours=16.0,
            hourly_rate=40.0,
        )
        client_cls.assert_not_called()
        async_cls.assert_not_called()
        get_fn.assert_not_called()
        post_fn.assert_not_called()

"""Unit tests for CounterOfferLeverageAdvisor."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from autoapply_agent.services.counter_offer_leverage import CounterOfferLeverageAdvisor


def test_strong_leverage() -> None:
    """Competing offer >=15% higher is strong."""

    report = CounterOfferLeverageAdvisor().advise(
        current_offer_tc=200_000.0,
        competing_offer_tc=240_000.0,
    )
    assert report.leverage_band == "strong"
    assert report.delta_pct == 20.0
    assert report.auto_send is False


def test_moderate_leverage() -> None:
    """Between 5% and 15% is moderate."""

    report = CounterOfferLeverageAdvisor().advise(
        current_offer_tc=200_000.0,
        competing_offer_tc=220_000.0,
    )
    assert report.leverage_band == "moderate"


def test_none_without_competing() -> None:
    """Zero competing offer is none."""

    report = CounterOfferLeverageAdvisor().advise(
        current_offer_tc=180_000.0,
        competing_offer_tc=0.0,
    )
    assert report.leverage_band == "none"


def test_invalid_current_raises() -> None:
    """Non-positive current_offer_tc raises ValueError."""

    with pytest.raises(ValueError, match="current_offer_tc"):
        CounterOfferLeverageAdvisor().advise(
            current_offer_tc=0.0,
            competing_offer_tc=100.0,
        )


def test_no_network_calls() -> None:
    """Advisor never performs HTTP calls."""

    with (
        patch("httpx.Client", MagicMock()) as client_cls,
        patch("httpx.AsyncClient", MagicMock()) as async_cls,
        patch("httpx.get", MagicMock()) as get_fn,
        patch("httpx.post", MagicMock()) as post_fn,
    ):
        CounterOfferLeverageAdvisor().advise(
            current_offer_tc=100_000.0,
            competing_offer_tc=110_000.0,
        )
        client_cls.assert_not_called()
        async_cls.assert_not_called()
        get_fn.assert_not_called()
        post_fn.assert_not_called()

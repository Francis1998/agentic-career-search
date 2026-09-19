"""Unit tests for EquityVestingCliffAdvisor."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from autoapply_agent.services.equity_vesting import EquityVestingCliffAdvisor


def test_pre_cliff_zero_vested() -> None:
    """Before cliff, vested value is zero."""

    report = EquityVestingCliffAdvisor().advise(
        grant_value=240_000.0,
        cliff_months=12,
        vest_months=48,
        months_elapsed=6,
    )
    assert report.vested_value == 0.0
    assert report.unvested_value == 240_000.0
    assert report.past_cliff is False
    assert report.vest_band == "pre_cliff"
    assert report.auto_accept is False
    assert report.requires_human_review is True


def test_mid_vest_linear() -> None:
    """At 24/48 months, half the grant is vested under linear schedule."""

    report = EquityVestingCliffAdvisor().advise(
        grant_value=240_000.0,
        cliff_months=12,
        vest_months=48,
        months_elapsed=24,
    )
    assert report.past_cliff is True
    assert report.vested_value == 120_000.0
    assert report.vest_band == "mid_vest"


def test_fully_vested() -> None:
    """At/after vest_months the full grant is vested."""

    report = EquityVestingCliffAdvisor().advise(
        grant_value=100_000.0,
        months_elapsed=48,
    )
    assert report.vested_value == 100_000.0
    assert report.unvested_value == 0.0
    assert report.vest_band == "mostly_vested"


def test_invalid_vest_window_raises() -> None:
    """vest_months <= cliff_months raises ValueError."""

    with pytest.raises(ValueError, match="vest_months"):
        EquityVestingCliffAdvisor().advise(
            grant_value=10.0,
            cliff_months=12,
            vest_months=12,
        )


def test_no_network_calls() -> None:
    """Advisor never performs HTTP calls."""

    with (
        patch("httpx.Client", MagicMock()) as client_cls,
        patch("httpx.AsyncClient", MagicMock()) as async_cls,
        patch("httpx.get", MagicMock()) as get_fn,
        patch("httpx.post", MagicMock()) as post_fn,
    ):
        EquityVestingCliffAdvisor().advise(grant_value=50_000.0, months_elapsed=12)
        client_cls.assert_not_called()
        async_cls.assert_not_called()
        get_fn.assert_not_called()
        post_fn.assert_not_called()

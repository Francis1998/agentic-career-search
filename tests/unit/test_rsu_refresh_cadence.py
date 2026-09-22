"""Unit tests for RsuRefreshCadenceAdvisor."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from autoapply_agent.services.rsu_refresh_cadence import RsuRefreshCadenceAdvisor


def test_on_cadence() -> None:
    """Recent refresh is on_cadence."""

    report = RsuRefreshCadenceAdvisor().advise(
        annual_refresh_value=40_000.0,
        years_since_refresh=0.5,
    )
    assert report.cadence_band == "on_cadence"
    assert report.accrued_value == 20_000.0
    assert report.auto_accept is False


def test_stale_refresh() -> None:
    """More than two years since refresh is stale."""

    report = RsuRefreshCadenceAdvisor().advise(
        annual_refresh_value=50_000.0,
        years_since_refresh=2.5,
    )
    assert report.cadence_band == "stale"
    assert report.accrued_value == 125_000.0


def test_overdue_band() -> None:
    """Between 1.25 and 2.0 years is overdue."""

    report = RsuRefreshCadenceAdvisor().advise(
        annual_refresh_value=20_000.0,
        years_since_refresh=1.5,
    )
    assert report.cadence_band == "overdue"


def test_invalid_vesting_raises() -> None:
    """Non-positive vesting_years raises ValueError."""

    with pytest.raises(ValueError, match="vesting_years"):
        RsuRefreshCadenceAdvisor().advise(
            annual_refresh_value=1.0,
            years_since_refresh=1.0,
            vesting_years=0,
        )


def test_no_network_calls() -> None:
    """Advisor never performs HTTP calls."""

    with (
        patch("httpx.Client", MagicMock()) as client_cls,
        patch("httpx.AsyncClient", MagicMock()) as async_cls,
        patch("httpx.get", MagicMock()) as get_fn,
        patch("httpx.post", MagicMock()) as post_fn,
    ):
        RsuRefreshCadenceAdvisor().advise(
            annual_refresh_value=10_000.0,
            years_since_refresh=1.0,
        )
        client_cls.assert_not_called()
        async_cls.assert_not_called()
        get_fn.assert_not_called()
        post_fn.assert_not_called()

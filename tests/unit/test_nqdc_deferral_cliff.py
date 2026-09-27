"""Unit tests for NqdcDeferralCliffAdvisor."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from autoapply_agent.services.nqdc_deferral_cliff import NqdcDeferralCliffAdvisor


def test_cliff_calm() -> None:
    """Distant small deferral is cliff_calm."""

    report = NqdcDeferralCliffAdvisor().advise(
        years_to_cliff=8.0,
        deferral_usd=50_000.0,
        tax_rate_delta=0.0,
    )
    assert report.cliff_band == "cliff_calm"
    assert report.auto_elect is False
    assert report.requires_human_review is True


def test_cliff_watch() -> None:
    """Mid-horizon deferral is cliff_watch."""

    report = NqdcDeferralCliffAdvisor().advise(
        years_to_cliff=2.5,
        deferral_usd=100_000.0,
        tax_rate_delta=0.05,
    )
    assert report.cliff_band == "cliff_watch"


def test_cliff_urgent() -> None:
    """Near cliff is cliff_urgent."""

    report = NqdcDeferralCliffAdvisor().advise(
        years_to_cliff=0.5,
        deferral_usd=200_000.0,
        tax_rate_delta=0.1,
    )
    assert report.cliff_band == "cliff_urgent"


def test_invalid_deferral_raises() -> None:
    """Non-positive deferral raises ValueError."""

    with pytest.raises(ValueError, match="deferral_usd"):
        NqdcDeferralCliffAdvisor().advise(
            years_to_cliff=2.0,
            deferral_usd=0.0,
            tax_rate_delta=0.0,
        )


def test_no_network_calls() -> None:
    """Advisor never performs HTTP calls."""

    with (
        patch("httpx.Client", MagicMock()) as client_cls,
        patch("httpx.AsyncClient", MagicMock()) as async_cls,
        patch("httpx.get", MagicMock()) as get_fn,
        patch("httpx.post", MagicMock()) as post_fn,
    ):
        NqdcDeferralCliffAdvisor().advise(
            years_to_cliff=4.0,
            deferral_usd=75_000.0,
            tax_rate_delta=-0.02,
        )
        client_cls.assert_not_called()
        async_cls.assert_not_called()
        get_fn.assert_not_called()
        post_fn.assert_not_called()

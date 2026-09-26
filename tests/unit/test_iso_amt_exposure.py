"""Unit tests for IsoAmtExposureAdvisor."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from autoapply_agent.services.iso_amt_exposure import IsoAmtExposureAdvisor


def test_low_exposure() -> None:
    """Bargain element well under exemption is low_exposure."""

    report = IsoAmtExposureAdvisor().advise(
        shares_exercised=100,
        fmv_at_exercise=12.0,
        strike_price=10.0,
        amt_exemption_usd=80000.0,
    )
    assert report.exposure_band == "low_exposure"
    assert report.auto_exercise is False
    assert report.requires_human_review is True


def test_moderate_exposure() -> None:
    """Bargain element between 25% and 100% of exemption is moderate."""

    report = IsoAmtExposureAdvisor().advise(
        shares_exercised=2000,
        fmv_at_exercise=30.0,
        strike_price=10.0,
        amt_exemption_usd=80000.0,
    )
    assert report.exposure_band == "moderate_exposure"
    assert report.bargain_element_usd == 40000.0


def test_high_exposure() -> None:
    """Bargain element at/above exemption is high_exposure."""

    report = IsoAmtExposureAdvisor().advise(
        shares_exercised=10000,
        fmv_at_exercise=30.0,
        strike_price=10.0,
        amt_exemption_usd=80000.0,
    )
    assert report.exposure_band == "high_exposure"


def test_invalid_strike_raises() -> None:
    """Negative strike raises ValueError."""

    with pytest.raises(ValueError, match="strike_price"):
        IsoAmtExposureAdvisor().advise(
            shares_exercised=10,
            fmv_at_exercise=20.0,
            strike_price=-1.0,
            amt_exemption_usd=80000.0,
        )


def test_no_network_calls() -> None:
    """Advisor never performs HTTP calls."""

    with (
        patch("httpx.Client", MagicMock()) as client_cls,
        patch("httpx.AsyncClient", MagicMock()) as async_cls,
        patch("httpx.get", MagicMock()) as get_fn,
        patch("httpx.post", MagicMock()) as post_fn,
    ):
        IsoAmtExposureAdvisor().advise(
            shares_exercised=10,
            fmv_at_exercise=20.0,
            strike_price=5.0,
            amt_exemption_usd=80000.0,
        )
        client_cls.assert_not_called()
        async_cls.assert_not_called()
        get_fn.assert_not_called()
        post_fn.assert_not_called()

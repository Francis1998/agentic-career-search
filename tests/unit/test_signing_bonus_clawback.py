"""Unit tests for SigningBonusClawbackAdvisor."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from autoapply_agent.services.signing_bonus_clawback import SigningBonusClawbackAdvisor


def test_high_liability_early() -> None:
    """Early in the clawback window, most bonus remains liable."""

    report = SigningBonusClawbackAdvisor().advise(
        bonus_amount=20_000.0,
        clawback_months=12,
        months_elapsed=1,
    )
    assert report.clawback_band == "high_liability"
    assert report.remaining_liability == 18_333.33
    assert report.auto_accept is False
    assert report.requires_human_review is True


def test_mid_liability() -> None:
    """At halfway through clawback, half remains liable."""

    report = SigningBonusClawbackAdvisor().advise(
        bonus_amount=12_000.0,
        clawback_months=12,
        months_elapsed=6,
    )
    assert report.clawback_band == "mid_liability"
    assert report.remaining_liability == 6_000.0
    assert report.liability_fraction == 0.5


def test_cleared_after_window() -> None:
    """After clawback months, liability is cleared."""

    report = SigningBonusClawbackAdvisor().advise(
        bonus_amount=10_000.0,
        clawback_months=12,
        months_elapsed=12,
    )
    assert report.clawback_band == "cleared"
    assert report.remaining_liability == 0.0


def test_invalid_clawback_months_raises() -> None:
    """Non-positive clawback_months raises ValueError."""

    with pytest.raises(ValueError, match="clawback_months"):
        SigningBonusClawbackAdvisor().advise(bonus_amount=1.0, clawback_months=0)


def test_no_network_calls() -> None:
    """Advisor never performs HTTP calls."""

    with (
        patch("httpx.Client", MagicMock()) as client_cls,
        patch("httpx.AsyncClient", MagicMock()) as async_cls,
        patch("httpx.get", MagicMock()) as get_fn,
        patch("httpx.post", MagicMock()) as post_fn,
    ):
        SigningBonusClawbackAdvisor().advise(bonus_amount=5_000.0, months_elapsed=3)
        client_cls.assert_not_called()
        async_cls.assert_not_called()
        get_fn.assert_not_called()
        post_fn.assert_not_called()

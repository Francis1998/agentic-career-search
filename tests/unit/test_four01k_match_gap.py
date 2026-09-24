"""Unit tests for FourOhOneKMatchGapAdvisor."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from autoapply_agent.services.four01k_match_gap import FourOhOneKMatchGapAdvisor


def test_gap_band_when_employer_trails() -> None:
    """Employer match trailing market by >=2% of salary is gap."""

    report = FourOhOneKMatchGapAdvisor().advise(
        employer_match_pct=3.0,
        market_match_pct=6.0,
        salary=100_000.0,
    )
    assert report.coverage_band == "gap"
    assert report.annual_gap_usd == 3_000.0
    assert report.auto_enroll is False


def test_strong_when_employer_beats_market() -> None:
    """Employer match at or above market is strong."""

    report = FourOhOneKMatchGapAdvisor().advise(
        employer_match_pct=6.0,
        market_match_pct=4.0,
        salary=120_000.0,
    )
    assert report.coverage_band == "strong"
    assert report.annual_gap_usd == -2_400.0


def test_parity_small_gap() -> None:
    """Small positive gap under 2% of salary is parity."""

    report = FourOhOneKMatchGapAdvisor().advise(
        employer_match_pct=5.0,
        market_match_pct=6.0,
        salary=100_000.0,
    )
    assert report.coverage_band == "parity"
    assert report.annual_gap_usd == 1_000.0


def test_invalid_salary_raises() -> None:
    """Non-positive salary raises ValueError."""

    with pytest.raises(ValueError, match="salary"):
        FourOhOneKMatchGapAdvisor().advise(
            employer_match_pct=3.0,
            market_match_pct=6.0,
            salary=0.0,
        )


def test_no_network_calls() -> None:
    """Advisor never performs HTTP calls."""

    with (
        patch("httpx.Client", MagicMock()) as client_cls,
        patch("httpx.AsyncClient", MagicMock()) as async_cls,
        patch("httpx.get", MagicMock()) as get_fn,
        patch("httpx.post", MagicMock()) as post_fn,
    ):
        FourOhOneKMatchGapAdvisor().advise(
            employer_match_pct=4.0,
            market_match_pct=4.0,
            salary=90_000.0,
        )
        client_cls.assert_not_called()
        async_cls.assert_not_called()
        get_fn.assert_not_called()
        post_fn.assert_not_called()

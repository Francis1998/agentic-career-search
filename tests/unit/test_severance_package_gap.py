"""Unit tests for SeverancePackageGapAdvisor."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from autoapply_agent.services.severance_package_gap import SeverancePackageGapAdvisor


def test_meets_or_exceeds() -> None:
    """Offered weeks at or above expectation band as meets_or_exceeds."""

    report = SeverancePackageGapAdvisor().advise(tenure_years=4.0, offered_weeks=10.0)
    assert report.coverage_band == "meets_or_exceeds"
    assert report.expected_weeks == 8.0
    assert report.auto_accept is False
    assert report.requires_human_review is True


def test_severe_gap() -> None:
    """Very low offered weeks relative to tenure are a severe_gap."""

    report = SeverancePackageGapAdvisor().advise(tenure_years=10.0, offered_weeks=2.0)
    assert report.coverage_band == "severe_gap"
    assert report.coverage_ratio < 0.4


def test_floor_weeks_applies() -> None:
    """Short tenure still uses floor_weeks expectation."""

    report = SeverancePackageGapAdvisor(floor_weeks=6.0).advise(
        tenure_years=0.5,
        offered_weeks=6.0,
    )
    assert report.expected_weeks == 6.0
    assert report.coverage_band == "meets_or_exceeds"


def test_invalid_tenure_raises() -> None:
    """Negative tenure_years raises ValueError."""

    with pytest.raises(ValueError, match="tenure_years"):
        SeverancePackageGapAdvisor().advise(tenure_years=-1.0, offered_weeks=4.0)


def test_no_network_calls() -> None:
    """Advisor never performs HTTP calls."""

    with (
        patch("httpx.Client", MagicMock()) as client_cls,
        patch("httpx.AsyncClient", MagicMock()) as async_cls,
        patch("httpx.get", MagicMock()) as get_fn,
        patch("httpx.post", MagicMock()) as post_fn,
    ):
        SeverancePackageGapAdvisor().advise(tenure_years=3.0, offered_weeks=4.0)
        client_cls.assert_not_called()
        async_cls.assert_not_called()
        get_fn.assert_not_called()
        post_fn.assert_not_called()

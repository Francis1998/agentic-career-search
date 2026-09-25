"""Unit tests for OnCallStipendGapAdvisor."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from autoapply_agent.services.oncall_stipend_gap import OnCallStipendGapAdvisor


def test_adequate_band() -> None:
    """Strong stipend vs light load is adequate."""

    report = OnCallStipendGapAdvisor().advise(
        weekly_oncall_hours=10.0,
        hourly_oncall_rate=50.0,
        monthly_flat_stipend=0.0,
        expected_pages_per_week=1.0,
    )
    assert report.value_band == "adequate"
    assert report.auto_accept is False


def test_underpaid_band() -> None:
    """Tiny stipend vs heavy load is underpaid."""

    report = OnCallStipendGapAdvisor().advise(
        weekly_oncall_hours=40.0,
        hourly_oncall_rate=0.0,
        monthly_flat_stipend=50.0,
        expected_pages_per_week=20.0,
    )
    assert report.value_band == "underpaid"
    assert report.requires_human_review is True


def test_no_load() -> None:
    """Zero hours and pages is no_load."""

    report = OnCallStipendGapAdvisor().advise(
        weekly_oncall_hours=0.0,
        monthly_flat_stipend=100.0,
    )
    assert report.value_band == "no_load"


def test_invalid_hours_raises() -> None:
    """Negative hours raises ValueError."""

    with pytest.raises(ValueError, match="weekly_oncall_hours"):
        OnCallStipendGapAdvisor().advise(weekly_oncall_hours=-1.0)


def test_no_network_calls() -> None:
    """Advisor never performs HTTP calls."""

    with (
        patch("httpx.Client", MagicMock()) as client_cls,
        patch("httpx.AsyncClient", MagicMock()) as async_cls,
        patch("httpx.get", MagicMock()) as get_fn,
        patch("httpx.post", MagicMock()) as post_fn,
    ):
        OnCallStipendGapAdvisor().advise(
            weekly_oncall_hours=20.0,
            hourly_oncall_rate=15.0,
            expected_pages_per_week=5.0,
        )
        client_cls.assert_not_called()
        async_cls.assert_not_called()
        get_fn.assert_not_called()
        post_fn.assert_not_called()

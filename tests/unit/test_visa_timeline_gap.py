"""Unit tests for VisaTimelineGapAdvisor."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from autoapply_agent.services.visa_timeline_gap import (
    VisaTimelineGapAdvisor,
)


def test_well_covered() -> None:
    """Band well_covered."""

    report = VisaTimelineGapAdvisor().advise(
        days_to_start=120.0,
        estimated_processing_days=60.0,
        buffer_days=14.0,
    )
    assert report.coverage_band == "well_covered"
    assert report.auto_enroll is False
    assert report.requires_human_review is True


def test_partial_gap() -> None:
    """Band partial_gap."""

    report = VisaTimelineGapAdvisor().advise(
        days_to_start=50.0,
        estimated_processing_days=60.0,
        buffer_days=14.0,
    )
    assert report.coverage_band == "partial_gap"


def test_under_covered() -> None:
    """Band under_covered."""

    report = VisaTimelineGapAdvisor().advise(
        days_to_start=20.0,
        estimated_processing_days=90.0,
        buffer_days=14.0,
    )
    assert report.coverage_band == "under_covered"


def test_invalid_raises() -> None:
    """Invalid numeric input raises ValueError."""

    with pytest.raises(ValueError, match="estimated_processing_days"):
        VisaTimelineGapAdvisor().advise(
            days_to_start=30.0,
            estimated_processing_days=0.0,
            buffer_days=0.0,
        )


def test_no_network_calls() -> None:
    """Advisor never performs HTTP calls."""

    with (
        patch("httpx.Client", MagicMock()) as client_cls,
        patch("httpx.AsyncClient", MagicMock()) as async_cls,
        patch("httpx.get", MagicMock()) as get_fn,
        patch("httpx.post", MagicMock()) as post_fn,
    ):
        VisaTimelineGapAdvisor().advise(
            days_to_start=50.0,
            estimated_processing_days=60.0,
            buffer_days=14.0,
        )
        client_cls.assert_not_called()
        async_cls.assert_not_called()
        get_fn.assert_not_called()
        post_fn.assert_not_called()

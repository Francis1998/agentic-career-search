"""Unit tests for MentalHealthEapSessionGapAdvisor."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from autoapply_agent.services.mental_health_eap_session_gap import MentalHealthEapSessionGapAdvisor


def test_well_covered() -> None:
    """Band well_covered."""

    report = MentalHealthEapSessionGapAdvisor().advise(
        needed_sessions_per_year=1000.0,
        employer_session_cap=1500.0,
        planned_sessions=1000.0,
    )
    assert report.coverage_band == "well_covered"
    assert report.auto_book is False
    assert report.requires_human_review is True


def test_partial_gap() -> None:
    """Band partial_gap."""

    report = MentalHealthEapSessionGapAdvisor().advise(
        needed_sessions_per_year=2000.0,
        employer_session_cap=1200.0,
        planned_sessions=1200.0,
    )
    assert report.coverage_band == "partial_gap"


def test_under_covered() -> None:
    """Band under_covered."""

    report = MentalHealthEapSessionGapAdvisor().advise(
        needed_sessions_per_year=3000.0,
        employer_session_cap=500.0,
        planned_sessions=500.0,
    )
    assert report.coverage_band == "under_covered"


def test_invalid_raises() -> None:
    """Non-positive employer amount raises ValueError."""

    with pytest.raises(ValueError, match="employer_session_cap"):
        MentalHealthEapSessionGapAdvisor().advise(
            needed_sessions_per_year=1000.0,
            employer_session_cap=0.0,
            planned_sessions=0.0,
        )


def test_no_network_calls() -> None:
    """Advisor never performs HTTP calls."""

    with (
        patch("httpx.Client", MagicMock()) as client_cls,
        patch("httpx.AsyncClient", MagicMock()) as async_cls,
        patch("httpx.get", MagicMock()) as get_fn,
        patch("httpx.post", MagicMock()) as post_fn,
    ):
        MentalHealthEapSessionGapAdvisor().advise(
            needed_sessions_per_year=2000.0,
            employer_session_cap=1200.0,
            planned_sessions=1200.0,
        )
        client_cls.assert_not_called()
        async_cls.assert_not_called()
        get_fn.assert_not_called()
        post_fn.assert_not_called()

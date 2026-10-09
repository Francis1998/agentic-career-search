"""Unit tests for GardenLeaveGapAdvisor."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from autoapply_agent.services.garden_leave_gap import GardenLeaveGapAdvisor


def test_well_covered() -> None:
    """Band well_covered."""

    report = GardenLeaveGapAdvisor().advise(
        garden_leave_days=120.0,
        needed_transition_days=60.0,
    )
    assert report.coverage_band == "well_covered"
    assert report.auto_enroll is False
    assert report.requires_human_review is True


def test_partial_gap() -> None:
    """Band partial_gap."""

    report = GardenLeaveGapAdvisor().advise(
        garden_leave_days=50.0,
        needed_transition_days=60.0,
    )
    assert report.coverage_band == "partial_gap"


def test_under_covered() -> None:
    """Band under_covered."""

    report = GardenLeaveGapAdvisor().advise(
        garden_leave_days=20.0,
        needed_transition_days=90.0,
    )
    assert report.coverage_band == "under_covered"


def test_invalid_raises() -> None:
    """Invalid numeric input raises ValueError."""

    with pytest.raises(ValueError, match="needed_transition_days"):
        GardenLeaveGapAdvisor().advise(
            garden_leave_days=30.0,
            needed_transition_days=0.0,
        )


def test_no_network_calls() -> None:
    """Advisor never performs HTTP calls."""

    with (
        patch("httpx.Client", MagicMock()) as client_cls,
        patch("httpx.AsyncClient", MagicMock()) as async_cls,
        patch("httpx.get", MagicMock()) as get_fn,
        patch("httpx.post", MagicMock()) as post_fn,
    ):
        GardenLeaveGapAdvisor().advise(
            garden_leave_days=50.0,
            needed_transition_days=60.0,
        )
        client_cls.assert_not_called()
        async_cls.assert_not_called()
        get_fn.assert_not_called()
        post_fn.assert_not_called()

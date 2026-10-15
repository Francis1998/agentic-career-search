"""Unit tests for ChildcareSubsidyGapAdvisor."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from autoapply_agent.services.childcare_subsidy_gap import ChildcareSubsidyGapAdvisor


def test_well_covered() -> None:
    """Band well_covered."""

    report = ChildcareSubsidyGapAdvisor().advise(
        offered_subsidy_usd=100.0,
        needed_subsidy_usd=100.0,
    )
    assert report.coverage_band == "well_covered"
    assert report.auto_enroll is False
    assert report.requires_human_review is True


def test_partial_gap() -> None:
    """Band partial_gap."""

    report = ChildcareSubsidyGapAdvisor().advise(
        offered_subsidy_usd=60.0,
        needed_subsidy_usd=100.0,
    )
    assert report.coverage_band == "partial_gap"


def test_under_covered() -> None:
    """Band under_covered."""

    report = ChildcareSubsidyGapAdvisor().advise(
        offered_subsidy_usd=20.0,
        needed_subsidy_usd=100.0,
    )
    assert report.coverage_band == "under_covered"


def test_invalid_raises() -> None:
    """Invalid numeric input raises ValueError."""

    with pytest.raises(ValueError, match="needed_subsidy_usd"):
        ChildcareSubsidyGapAdvisor().advise(
            offered_subsidy_usd=10.0,
            needed_subsidy_usd=0.0,
        )


def test_no_network_calls() -> None:
    """Advisor never performs HTTP calls."""

    with (
        patch("httpx.Client", MagicMock()) as client_cls,
        patch("httpx.AsyncClient", MagicMock()) as async_cls,
        patch("httpx.get", MagicMock()) as get_fn,
        patch("httpx.post", MagicMock()) as post_fn,
    ):
        ChildcareSubsidyGapAdvisor().advise(
            offered_subsidy_usd=50.0,
            needed_subsidy_usd=100.0,
        )
        client_cls.assert_not_called()
        async_cls.assert_not_called()
        get_fn.assert_not_called()
        post_fn.assert_not_called()

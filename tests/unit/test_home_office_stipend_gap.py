"""Unit tests for HomeOfficeStipendGapAdvisor."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from autoapply_agent.services.home_office_stipend_gap import HomeOfficeStipendGapAdvisor


def test_fully_covered() -> None:
    """Stipend >= setup cost is fully_covered."""

    report = HomeOfficeStipendGapAdvisor().advise(
        stipend_annual_usd=1000.0,
        setup_cost_usd=800.0,
    )
    assert report.coverage_band == "fully_covered"
    assert report.auto_accept is False
    assert report.requires_human_review is True


def test_partial_coverage() -> None:
    """Coverage between 0.6 and 1.0 is partial."""

    report = HomeOfficeStipendGapAdvisor().advise(
        stipend_annual_usd=700.0,
        setup_cost_usd=1000.0,
    )
    assert report.coverage_band == "partial"


def test_underfunded() -> None:
    """Coverage below 0.6 is underfunded."""

    report = HomeOfficeStipendGapAdvisor().advise(
        stipend_annual_usd=200.0,
        setup_cost_usd=1000.0,
    )
    assert report.coverage_band == "underfunded"
    assert report.gap_usd == 800.0


def test_invalid_setup_cost_raises() -> None:
    """Non-positive setup cost raises ValueError."""

    with pytest.raises(ValueError, match="setup_cost_usd"):
        HomeOfficeStipendGapAdvisor().advise(
            stipend_annual_usd=500.0,
            setup_cost_usd=0.0,
        )


def test_no_network_calls() -> None:
    """Advisor never performs HTTP calls."""

    with (
        patch("httpx.Client", MagicMock()) as client_cls,
        patch("httpx.AsyncClient", MagicMock()) as async_cls,
        patch("httpx.get", MagicMock()) as get_fn,
        patch("httpx.post", MagicMock()) as post_fn,
    ):
        HomeOfficeStipendGapAdvisor().advise(
            stipend_annual_usd=500.0,
            setup_cost_usd=900.0,
        )
        client_cls.assert_not_called()
        async_cls.assert_not_called()
        get_fn.assert_not_called()
        post_fn.assert_not_called()

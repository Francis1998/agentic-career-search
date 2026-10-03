"""Unit tests for EmergencyFundRunwayAdvisor."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from autoapply_agent.services.emergency_fund_runway import (
    EmergencyFundRunwayAdvisor,
)


def test_well_covered() -> None:
    """Band well_covered."""

    report = EmergencyFundRunwayAdvisor().advise(
        liquid_savings_usd=18000.0,
        monthly_burn_usd=3000.0,
        target_months=6.0,
    )
    assert report.coverage_band == "well_covered"
    assert report.auto_enroll is False
    assert report.requires_human_review is True


def test_partial_gap() -> None:
    """Band partial_gap."""

    report = EmergencyFundRunwayAdvisor().advise(
        liquid_savings_usd=9000.0,
        monthly_burn_usd=3000.0,
        target_months=6.0,
    )
    assert report.coverage_band == "partial_gap"


def test_under_covered() -> None:
    """Band under_covered."""

    report = EmergencyFundRunwayAdvisor().advise(
        liquid_savings_usd=2000.0,
        monthly_burn_usd=3000.0,
        target_months=6.0,
    )
    assert report.coverage_band == "under_covered"


def test_invalid_raises() -> None:
    """Invalid numeric input raises ValueError."""

    with pytest.raises(ValueError, match="monthly_burn_usd"):
        EmergencyFundRunwayAdvisor().advise(
            liquid_savings_usd=1000.0,
            monthly_burn_usd=0.0,
            target_months=6.0,
        )


def test_no_network_calls() -> None:
    """Advisor never performs HTTP calls."""

    with (
        patch("httpx.Client", MagicMock()) as client_cls,
        patch("httpx.AsyncClient", MagicMock()) as async_cls,
        patch("httpx.get", MagicMock()) as get_fn,
        patch("httpx.post", MagicMock()) as post_fn,
    ):
        EmergencyFundRunwayAdvisor().advise(
            liquid_savings_usd=9000.0,
            monthly_burn_usd=3000.0,
            target_months=6.0,
        )
        client_cls.assert_not_called()
        async_cls.assert_not_called()
        get_fn.assert_not_called()
        post_fn.assert_not_called()

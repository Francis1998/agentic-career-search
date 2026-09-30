"""Unit tests for IdentityTheftProtectionGapAdvisor."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from autoapply_agent.services.identity_theft_protection_gap import IdentityTheftProtectionGapAdvisor


def test_well_covered() -> None:
    """Band well_covered."""

    report = IdentityTheftProtectionGapAdvisor().advise(
        household_risk_budget_usd=1000.0,
        employer_benefit_usd=1500.0,
        planned_claim_usd=1000.0,
    )
    assert report.coverage_band == "well_covered"
    assert report.auto_claim is False
    assert report.requires_human_review is True


def test_partial_gap() -> None:
    """Band partial_gap."""

    report = IdentityTheftProtectionGapAdvisor().advise(
        household_risk_budget_usd=2000.0,
        employer_benefit_usd=1200.0,
        planned_claim_usd=1200.0,
    )
    assert report.coverage_band == "partial_gap"


def test_under_covered() -> None:
    """Band under_covered."""

    report = IdentityTheftProtectionGapAdvisor().advise(
        household_risk_budget_usd=3000.0,
        employer_benefit_usd=500.0,
        planned_claim_usd=500.0,
    )
    assert report.coverage_band == "under_covered"


def test_invalid_raises() -> None:
    """Non-positive limit raises ValueError."""

    with pytest.raises(ValueError, match="employer_benefit_usd"):
        IdentityTheftProtectionGapAdvisor().advise(
            household_risk_budget_usd=1000.0,
            employer_benefit_usd=0.0,
            planned_claim_usd=0.0,
        )


def test_no_network_calls() -> None:
    """Advisor never performs HTTP calls."""

    with (
        patch("httpx.Client", MagicMock()) as client_cls,
        patch("httpx.AsyncClient", MagicMock()) as async_cls,
        patch("httpx.get", MagicMock()) as get_fn,
        patch("httpx.post", MagicMock()) as post_fn,
    ):
        IdentityTheftProtectionGapAdvisor().advise(
            household_risk_budget_usd=2000.0,
            employer_benefit_usd=1200.0,
            planned_claim_usd=1200.0,
        )
        client_cls.assert_not_called()
        async_cls.assert_not_called()
        get_fn.assert_not_called()
        post_fn.assert_not_called()

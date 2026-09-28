"""Unit tests for FertilityBenefitGapAdvisor."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from autoapply_agent.services.fertility_benefit_gap import FertilityBenefitGapAdvisor


def test_well_covered() -> None:
    """High coverage ratio is well_covered."""

    report = FertilityBenefitGapAdvisor().advise(
        annual_treatment_usd=15000.0,
        employer_cap_usd=25000.0,
        planned_claim_usd=15000.0,
    )
    assert report.coverage_band == "well_covered"
    assert report.auto_claim is False
    assert report.requires_human_review is True


def test_partial_gap() -> None:
    """Mid coverage is partial_gap."""

    report = FertilityBenefitGapAdvisor().advise(
        annual_treatment_usd=20000.0,
        employer_cap_usd=12000.0,
        planned_claim_usd=12000.0,
    )
    assert report.coverage_band == "partial_gap"


def test_under_covered() -> None:
    """Low coverage is under_covered."""

    report = FertilityBenefitGapAdvisor().advise(
        annual_treatment_usd=30000.0,
        employer_cap_usd=5000.0,
        planned_claim_usd=5000.0,
    )
    assert report.coverage_band == "under_covered"


def test_invalid_cap_raises() -> None:
    """Non-positive employer cap raises ValueError."""

    with pytest.raises(ValueError, match="employer_cap_usd"):
        FertilityBenefitGapAdvisor().advise(
            annual_treatment_usd=1000.0,
            employer_cap_usd=0.0,
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
        FertilityBenefitGapAdvisor().advise(
            annual_treatment_usd=18000.0,
            employer_cap_usd=10000.0,
            planned_claim_usd=8000.0,
        )
        client_cls.assert_not_called()
        async_cls.assert_not_called()
        get_fn.assert_not_called()
        post_fn.assert_not_called()

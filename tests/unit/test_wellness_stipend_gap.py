"""Unit tests for WellnessStipendGapAdvisor."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from autoapply_agent.services.wellness_stipend_gap import WellnessStipendGapAdvisor


def test_well_covered() -> None:
    """Band well_covered."""

    report = WellnessStipendGapAdvisor().advise(
        annual_wellness_spend_usd=900.0,
        employer_stipend_usd=1200.0,
        planned_claim_usd=900.0,
    )
    assert report.coverage_band == "well_covered"
    assert report.auto_claim is False
    assert report.requires_human_review is True


def test_partial_gap() -> None:
    """Band partial_gap."""

    report = WellnessStipendGapAdvisor().advise(
        annual_wellness_spend_usd=1600.0,
        employer_stipend_usd=900.0,
        planned_claim_usd=900.0,
    )
    assert report.coverage_band == "partial_gap"


def test_under_covered() -> None:
    """Band under_covered."""

    report = WellnessStipendGapAdvisor().advise(
        annual_wellness_spend_usd=2400.0,
        employer_stipend_usd=400.0,
        planned_claim_usd=400.0,
    )
    assert report.coverage_band == "under_covered"


def test_invalid_raises() -> None:
    """Non-positive limit raises ValueError."""

    with pytest.raises(ValueError, match="employer_stipend_usd"):
        WellnessStipendGapAdvisor().advise(
            annual_wellness_spend_usd=1000.0,
            employer_stipend_usd=0.0,
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
        WellnessStipendGapAdvisor().advise(
            annual_wellness_spend_usd=1600.0,
            employer_stipend_usd=900.0,
            planned_claim_usd=900.0,
        )
        client_cls.assert_not_called()
        async_cls.assert_not_called()
        get_fn.assert_not_called()
        post_fn.assert_not_called()

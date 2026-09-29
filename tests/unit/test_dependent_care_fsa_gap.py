"""Unit tests for DependentCareFsaGapAdvisor."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from autoapply_agent.services.dependent_care_fsa_gap import DependentCareFsaGapAdvisor


def test_well_covered() -> None:
    """Band well_covered."""

    report = DependentCareFsaGapAdvisor().advise(
        annual_daycare_usd=5000.0,
        dcfsa_limit_usd=5000.0,
        planned_contribution_usd=5000.0,
    )
    assert report.coverage_band == "well_covered"
    assert report.auto_enroll is False
    assert report.requires_human_review is True


def test_partial_gap() -> None:
    """Band partial_gap."""

    report = DependentCareFsaGapAdvisor().advise(
        annual_daycare_usd=9000.0,
        dcfsa_limit_usd=5000.0,
        planned_contribution_usd=5000.0,
    )
    assert report.coverage_band == "partial_gap"


def test_under_covered() -> None:
    """Band under_covered."""

    report = DependentCareFsaGapAdvisor().advise(
        annual_daycare_usd=15000.0,
        dcfsa_limit_usd=3000.0,
        planned_contribution_usd=3000.0,
    )
    assert report.coverage_band == "under_covered"


def test_invalid_raises() -> None:
    """Non-positive limit raises ValueError."""

    with pytest.raises(ValueError, match="dcfsa_limit_usd"):
        DependentCareFsaGapAdvisor().advise(
            annual_daycare_usd=1000.0,
            dcfsa_limit_usd=0.0,
            planned_contribution_usd=0.0,
        )


def test_no_network_calls() -> None:
    """Advisor never performs HTTP calls."""

    with (
        patch("httpx.Client", MagicMock()) as client_cls,
        patch("httpx.AsyncClient", MagicMock()) as async_cls,
        patch("httpx.get", MagicMock()) as get_fn,
        patch("httpx.post", MagicMock()) as post_fn,
    ):
        DependentCareFsaGapAdvisor().advise(
            annual_daycare_usd=9000.0,
            dcfsa_limit_usd=5000.0,
            planned_contribution_usd=5000.0,
        )
        client_cls.assert_not_called()
        async_cls.assert_not_called()
        get_fn.assert_not_called()
        post_fn.assert_not_called()

"""Unit tests for RetentionBonusCliffAdvisor."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from autoapply_agent.services.retention_bonus_cliff import RetentionBonusCliffAdvisor


def test_well_covered() -> None:
    """Band well_covered."""

    report = RetentionBonusCliffAdvisor().advise(
        months_to_cliff=120.0,
        target_buffer_months=60.0,
    )
    assert report.coverage_band == "well_covered"
    assert report.auto_enroll is False
    assert report.requires_human_review is True


def test_partial_gap() -> None:
    """Band partial_gap."""

    report = RetentionBonusCliffAdvisor().advise(
        months_to_cliff=50.0,
        target_buffer_months=60.0,
    )
    assert report.coverage_band == "partial_gap"


def test_under_covered() -> None:
    """Band under_covered."""

    report = RetentionBonusCliffAdvisor().advise(
        months_to_cliff=20.0,
        target_buffer_months=90.0,
    )
    assert report.coverage_band == "under_covered"


def test_invalid_raises() -> None:
    """Invalid numeric input raises ValueError."""

    with pytest.raises(ValueError, match="target_buffer_months"):
        RetentionBonusCliffAdvisor().advise(
            months_to_cliff=30.0,
            target_buffer_months=0.0,
        )


def test_no_network_calls() -> None:
    """Advisor never performs HTTP calls."""

    with (
        patch("httpx.Client", MagicMock()) as client_cls,
        patch("httpx.AsyncClient", MagicMock()) as async_cls,
        patch("httpx.get", MagicMock()) as get_fn,
        patch("httpx.post", MagicMock()) as post_fn,
    ):
        RetentionBonusCliffAdvisor().advise(
            months_to_cliff=50.0,
            target_buffer_months=60.0,
        )
        client_cls.assert_not_called()
        async_cls.assert_not_called()
        get_fn.assert_not_called()
        post_fn.assert_not_called()

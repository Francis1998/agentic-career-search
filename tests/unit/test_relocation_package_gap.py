"""Unit tests for RelocationPackageGapAdvisor."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from autoapply_agent.services.relocation_package_gap import RelocationPackageGapAdvisor


def test_large_gap() -> None:
    """Low stipend vs high move cost yields large_gap."""

    report = RelocationPackageGapAdvisor().advise(
        offered_stipend=2_000.0,
        estimated_move_cost=10_000.0,
    )
    assert report.coverage_band == "large_gap"
    assert report.gap_amount == 8_000.0
    assert report.auto_accept is False
    assert report.requires_human_review is True


def test_fully_covered() -> None:
    """Stipend >= cost yields fully_covered."""

    report = RelocationPackageGapAdvisor().advise(
        offered_stipend=12_000.0,
        estimated_move_cost=10_000.0,
    )
    assert report.coverage_band == "fully_covered"
    assert report.gap_amount == -2_000.0


def test_partial_gap() -> None:
    """Mid coverage yields partial_gap."""

    report = RelocationPackageGapAdvisor().advise(
        offered_stipend=5_000.0,
        estimated_move_cost=10_000.0,
    )
    assert report.coverage_band == "partial_gap"
    assert report.coverage_ratio == 0.5


def test_negative_stipend_raises() -> None:
    """Negative stipend raises ValueError."""

    with pytest.raises(ValueError, match="offered_stipend"):
        RelocationPackageGapAdvisor().advise(
            offered_stipend=-1.0,
            estimated_move_cost=1.0,
        )


def test_no_network_calls() -> None:
    """Advisor never performs HTTP calls."""

    with (
        patch("httpx.Client", MagicMock()) as client_cls,
        patch("httpx.AsyncClient", MagicMock()) as async_cls,
        patch("httpx.get", MagicMock()) as get_fn,
        patch("httpx.post", MagicMock()) as post_fn,
    ):
        RelocationPackageGapAdvisor().advise(
            offered_stipend=3_000.0,
            estimated_move_cost=4_000.0,
        )
        client_cls.assert_not_called()
        async_cls.assert_not_called()
        get_fn.assert_not_called()
        post_fn.assert_not_called()

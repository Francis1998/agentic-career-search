"""Unit tests for BereavementLeaveGapAdvisor."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from autoapply_agent.services.bereavement_leave_gap import BereavementLeaveGapAdvisor


def test_well_covered() -> None:
    """Offered days >= needed is well_covered."""

    report = BereavementLeaveGapAdvisor().advise(offered_days=5.0, needed_days=3.0)
    assert report.coverage_band == "well_covered"
    assert report.auto_approve is False
    assert report.requires_human_review is True


def test_partial_gap() -> None:
    """Mid coverage is partial_gap."""

    report = BereavementLeaveGapAdvisor().advise(offered_days=3.0, needed_days=5.0)
    assert report.coverage_band == "partial_gap"


def test_under_covered() -> None:
    """Low coverage is under_covered."""

    report = BereavementLeaveGapAdvisor().advise(offered_days=1.0, needed_days=5.0)
    assert report.coverage_band == "under_covered"


def test_invalid_needed_raises() -> None:
    """Non-positive needed days raises ValueError."""

    with pytest.raises(ValueError, match="needed_days"):
        BereavementLeaveGapAdvisor().advise(offered_days=3.0, needed_days=0.0)


def test_no_network_calls() -> None:
    """Advisor never performs HTTP calls."""

    with (
        patch("httpx.Client", MagicMock()) as client_cls,
        patch("httpx.AsyncClient", MagicMock()) as async_cls,
        patch("httpx.get", MagicMock()) as get_fn,
        patch("httpx.post", MagicMock()) as post_fn,
    ):
        BereavementLeaveGapAdvisor().advise(offered_days=4.0, needed_days=5.0)
        client_cls.assert_not_called()
        async_cls.assert_not_called()
        get_fn.assert_not_called()
        post_fn.assert_not_called()

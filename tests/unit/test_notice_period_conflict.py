"""Unit tests for NoticePeriodConflictFlagger."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from autoapply_agent.services.notice_period_conflict import NoticePeriodConflictFlagger


def test_comfortable_slack() -> None:
    """Preferred start well after notice is comfortable."""

    report = NoticePeriodConflictFlagger().flag(
        notice_weeks=2.0,
        preferred_start_days=45.0,
    )
    assert report.conflict_band == "comfortable"
    assert report.slack_days == 31.0
    assert report.auto_accept is False


def test_hard_conflict() -> None:
    """Preferred start far before notice ends is hard_conflict."""

    report = NoticePeriodConflictFlagger().flag(
        notice_weeks=8.0,
        preferred_start_days=7.0,
    )
    assert report.conflict_band == "hard_conflict"
    assert report.slack_days < -14


def test_tight_band() -> None:
    """Start exactly at notice end is tight."""

    report = NoticePeriodConflictFlagger().flag(
        notice_weeks=2.0,
        preferred_start_days=14.0,
    )
    assert report.conflict_band == "tight"
    assert report.slack_days == 0.0


def test_invalid_notice_raises() -> None:
    """Negative notice_weeks raises ValueError."""

    with pytest.raises(ValueError, match="notice_weeks"):
        NoticePeriodConflictFlagger().flag(notice_weeks=-1.0, preferred_start_days=10.0)


def test_no_network_calls() -> None:
    """Flagger never performs HTTP calls."""

    with (
        patch("httpx.Client", MagicMock()) as client_cls,
        patch("httpx.AsyncClient", MagicMock()) as async_cls,
        patch("httpx.get", MagicMock()) as get_fn,
        patch("httpx.post", MagicMock()) as post_fn,
    ):
        NoticePeriodConflictFlagger().flag(notice_weeks=2.0, preferred_start_days=21.0)
        client_cls.assert_not_called()
        async_cls.assert_not_called()
        get_fn.assert_not_called()
        post_fn.assert_not_called()

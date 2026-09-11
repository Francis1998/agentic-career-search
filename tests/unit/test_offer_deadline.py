"""Unit tests for OfferDeadlineTracker."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from autoapply_agent.services.offer_deadline import OfferDeadlineTracker

if TYPE_CHECKING:
    from _pytest.capture import CaptureFixture
    from _pytest.fixtures import FixtureRequest
    from _pytest.logging import LogCaptureFixture
    from _pytest.monkeypatch import MonkeyPatch
    from pytest_mock.plugin import MockerFixture


def test_empty_company_raises() -> None:
    """Blank company name raises ValueError."""

    with pytest.raises(ValueError, match="company"):
        OfferDeadlineTracker().track(
            company=" ",
            role="SWE",
            deadline_iso="2026-09-15",
            now_iso="2026-09-11",
        )


def test_bad_date_raises() -> None:
    """Invalid ISO dates raise ValueError."""

    with pytest.raises(ValueError, match="deadline_iso"):
        OfferDeadlineTracker().track(
            company="Acme",
            role="SWE",
            deadline_iso="not-a-date",
            now_iso="2026-09-11",
        )


def test_overdue_urgency() -> None:
    """Negative days_remaining maps to overdue."""

    status = OfferDeadlineTracker().track(
        company="Acme",
        role="Platform Engineer",
        deadline_iso="2026-09-08",
        now_iso="2026-09-11",
    )
    assert status.days_remaining == -3
    assert status.urgency == "overdue"
    assert any("never auto-decline" in item.lower() for item in status.reminders)


def test_due_today_urgency() -> None:
    """Zero days_remaining maps to due_today."""

    status = OfferDeadlineTracker().track(
        company="Acme",
        role="SWE",
        deadline_iso="2026-09-11",
        now_iso="2026-09-11",
    )
    assert status.days_remaining == 0
    assert status.urgency == "due_today"


def test_due_soon_urgency() -> None:
    """1-3 days remaining maps to due_soon."""

    status = OfferDeadlineTracker().track(
        company="Acme",
        role="SWE",
        deadline_iso="2026-09-13",
        now_iso="2026-09-11",
    )
    assert status.days_remaining == 2
    assert status.urgency == "due_soon"


def test_never_auto_declines_requires_human_review() -> None:
    """Every payload flags HITL review and never auto-declines."""

    status = OfferDeadlineTracker().track(
        company="Globex",
        role="SRE",
        deadline_iso="2026-09-20",
        now_iso="2026-09-11",
    )
    assert status.requires_human_review is True
    assert status.auto_decline is False
    assert status.urgency == "upcoming"
    assert status.reminders


def test_no_network_calls() -> None:
    """Tracker never performs HTTP calls."""

    with (
        patch("httpx.Client", MagicMock()) as client_cls,
        patch("httpx.AsyncClient", MagicMock()) as async_cls,
        patch("httpx.get", MagicMock()) as get_fn,
        patch("httpx.post", MagicMock()) as post_fn,
    ):
        OfferDeadlineTracker().track(
            company="Acme",
            role="SWE",
            deadline_iso="2026-09-15",
            now_iso="2026-09-11",
        )
        client_cls.assert_not_called()
        async_cls.assert_not_called()
        get_fn.assert_not_called()
        post_fn.assert_not_called()


def test_deterministic() -> None:
    """Repeated track calls are identical."""

    tracker = OfferDeadlineTracker()
    kwargs = {
        "company": "Acme",
        "role": "SWE",
        "deadline_iso": "2026-09-15",
        "now_iso": "2026-09-11",
    }
    assert tracker.track(**kwargs) == tracker.track(**kwargs)

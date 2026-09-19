"""Unit tests for InterviewRoundProgressTracker."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from autoapply_agent.services.interview_rounds import InterviewRoundProgressTracker


def test_happy_path_to_offer() -> None:
    """phone_screen → hiring_manager → onsite → offer succeeds."""

    tracker = InterviewRoundProgressTracker()
    snap = tracker.start("app-1")
    assert snap.round_name == "phone_screen"
    assert snap.auto_advance is False
    tracker.advance("app-1", "hiring_manager")
    tracker.advance("app-1", "onsite")
    final = tracker.advance("app-1", "offer")
    assert final.round_name == "offer"
    assert final.history == ["phone_screen", "hiring_manager", "onsite", "offer"]
    assert final.terminal is False
    assert final.requires_human_review is True


def test_illegal_skip_raises() -> None:
    """Skipping hiring_manager raises ValueError."""

    tracker = InterviewRoundProgressTracker()
    tracker.start("app-2")
    with pytest.raises(ValueError, match="illegal transition"):
        tracker.advance("app-2", "onsite")


def test_terminal_reject() -> None:
    """Rejecting from phone_screen is terminal."""

    tracker = InterviewRoundProgressTracker()
    tracker.start("app-3")
    snap = tracker.advance("app-3", "rejected")
    assert snap.terminal is True
    with pytest.raises(ValueError, match="terminal"):
        tracker.advance("app-3", "hiring_manager")


def test_duplicate_start_raises() -> None:
    """Starting the same application_id twice raises."""

    tracker = InterviewRoundProgressTracker()
    tracker.start("app-4")
    with pytest.raises(ValueError, match="already tracked"):
        tracker.start("app-4")


def test_no_network_calls() -> None:
    """Tracker never performs HTTP calls."""

    with (
        patch("httpx.Client", MagicMock()) as client_cls,
        patch("httpx.AsyncClient", MagicMock()) as async_cls,
        patch("httpx.get", MagicMock()) as get_fn,
        patch("httpx.post", MagicMock()) as post_fn,
    ):
        tracker = InterviewRoundProgressTracker()
        tracker.start("app-5")
        tracker.advance("app-5", "hiring_manager")
        client_cls.assert_not_called()
        async_cls.assert_not_called()
        get_fn.assert_not_called()
        post_fn.assert_not_called()

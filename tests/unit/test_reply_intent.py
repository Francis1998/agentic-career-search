"""Unit tests for RecruiterReplyIntentClassifier."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from autoapply_agent.services.reply_intent import RecruiterReplyIntentClassifier

if TYPE_CHECKING:
    from _pytest.capture import CaptureFixture
    from _pytest.fixtures import FixtureRequest
    from _pytest.logging import LogCaptureFixture
    from _pytest.monkeypatch import MonkeyPatch
    from pytest_mock.plugin import MockerFixture


def test_blank_reply_raises() -> None:
    """Blank reply_text raises ValueError."""

    with pytest.raises(ValueError, match="reply_text"):
        RecruiterReplyIntentClassifier().classify("  ")


def test_scheduling_intent() -> None:
    """Scheduling cues classify as scheduling."""

    report = RecruiterReplyIntentClassifier().classify(
        "Happy to schedule a 30 minutes Zoom phone screen — send availability."
    )
    names = {item.intent for item in report.intents}
    assert "scheduling" in names


def test_rejection_intent() -> None:
    """Rejection cues classify as rejection."""

    report = RecruiterReplyIntentClassifier().classify(
        "Unfortunately we are not moving forward and decided to proceed with other candidates."
    )
    names = {item.intent for item in report.intents}
    assert "rejection" in names


def test_uncategorized_still_hitl() -> None:
    """Unmatched text is uncategorized but still HITL."""

    report = RecruiterReplyIntentClassifier().classify("Thanks for sharing your portfolio.")
    assert report.uncategorized is True
    assert report.requires_human_review is True
    assert report.auto_send is False


def test_no_network_calls() -> None:
    """Classifier never performs HTTP calls."""

    with (
        patch("httpx.Client", MagicMock()) as client_cls,
        patch("httpx.AsyncClient", MagicMock()) as async_cls,
        patch("httpx.get", MagicMock()) as get_fn,
        patch("httpx.post", MagicMock()) as post_fn,
    ):
        RecruiterReplyIntentClassifier().classify("Excited to move forward with next steps.")
        client_cls.assert_not_called()
        async_cls.assert_not_called()
        get_fn.assert_not_called()
        post_fn.assert_not_called()

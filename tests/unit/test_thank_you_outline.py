"""Unit tests for ThankYouNoteOutlinePlanner."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from autoapply_agent.services.thank_you_outline import ThankYouNoteOutlinePlanner

if TYPE_CHECKING:
    from _pytest.capture import CaptureFixture
    from _pytest.fixtures import FixtureRequest
    from _pytest.logging import LogCaptureFixture
    from _pytest.monkeypatch import MonkeyPatch
    from pytest_mock.plugin import MockerFixture


def test_empty_company_raises() -> None:
    """Blank company raises ValueError."""

    with pytest.raises(ValueError, match="company"):
        ThankYouNoteOutlinePlanner().plan(
            company=" ",
            role="SWE",
            interviewer="Alex",
        )


def test_empty_role_raises() -> None:
    """Blank role raises ValueError."""

    with pytest.raises(ValueError, match="role"):
        ThankYouNoteOutlinePlanner().plan(
            company="Acme",
            role="",
            interviewer="Alex",
        )


def test_empty_interviewer_raises() -> None:
    """Blank interviewer raises ValueError."""

    with pytest.raises(ValueError, match="interviewer"):
        ThankYouNoteOutlinePlanner().plan(
            company="Acme",
            role="SWE",
            interviewer=" ",
        )


def test_bad_channel_raises() -> None:
    """Unknown channel raises ValueError."""

    with pytest.raises(ValueError, match="channel"):
        ThankYouNoteOutlinePlanner().plan(
            company="Acme",
            role="SWE",
            interviewer="Alex",
            channel="sms",
        )


def test_email_outline_with_highlights() -> None:
    """Email channel builds subject + highlight beats."""

    outline = ThankYouNoteOutlinePlanner().plan(
        company="Acme",
        role="Platform Engineer",
        interviewer="Alex Kim",
        highlights=["kafka lag dashboards", "on-call culture"],
        channel="email",
    )
    assert outline.channel == "email"
    assert "Thank you" in outline.subject
    assert any("kafka" in beat.lower() for beat in outline.beats)
    assert outline.requires_human_review is True
    assert outline.auto_send is False


def test_linkedin_outline_without_highlights() -> None:
    """LinkedIn channel still yields placeholder callback beat."""

    outline = ThankYouNoteOutlinePlanner().plan(
        company="Globex",
        role="SRE",
        interviewer="Sam",
        channel="linkedin",
    )
    assert outline.channel == "linkedin"
    assert any("callback" in beat.lower() for beat in outline.beats)
    assert outline.auto_send is False


def test_no_network_calls() -> None:
    """Planner never performs HTTP calls."""

    with (
        patch("httpx.Client", MagicMock()) as client_cls,
        patch("httpx.AsyncClient", MagicMock()) as async_cls,
        patch("httpx.get", MagicMock()) as get_fn,
        patch("httpx.post", MagicMock()) as post_fn,
    ):
        ThankYouNoteOutlinePlanner().plan(
            company="Acme",
            role="SWE",
            interviewer="Alex",
        )
        client_cls.assert_not_called()
        async_cls.assert_not_called()
        get_fn.assert_not_called()
        post_fn.assert_not_called()

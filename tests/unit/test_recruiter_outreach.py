"""Unit tests for RecruiterOutreachDraftService."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from autoapply_agent.services.recruiter_outreach import RecruiterOutreachDraftService

if TYPE_CHECKING:
    from _pytest.capture import CaptureFixture
    from _pytest.fixtures import FixtureRequest
    from _pytest.logging import LogCaptureFixture
    from _pytest.monkeypatch import MonkeyPatch
    from pytest_mock.plugin import MockerFixture


def test_empty_company_raises() -> None:
    """Blank company name raises ValueError."""

    with pytest.raises(ValueError, match="company"):
        RecruiterOutreachDraftService().generate(company="  ", role="SWE")


def test_invalid_channel_raises() -> None:
    """Unsupported channel raises ValueError."""

    with pytest.raises(ValueError, match="channel"):
        RecruiterOutreachDraftService().generate(
            company="Acme",
            role="SWE",
            channel="sms",
        )


def test_draft_always_requires_human_review() -> None:
    """Every draft flags requires_human_review=True and never auto-sends."""

    draft = RecruiterOutreachDraftService().generate(
        company="Acme",
        role="Platform Engineer",
        recruiter_name="Alex",
    )
    assert draft.requires_human_review is True
    assert draft.channel == "email"
    assert "Acme" in draft.subject
    assert "Platform Engineer" in draft.body
    assert "Alex" in draft.body
    assert draft.talking_points
    assert "do not auto-send" in draft.body.lower()


def test_linkedin_channel_draft() -> None:
    """LinkedIn channel produces a DM-style body with linkedin channel."""

    draft = RecruiterOutreachDraftService().generate(
        company="Nimbus",
        role="ML Engineer",
        channel="linkedin",
        notes="Shipped retrieval ranking in prod",
    )
    assert draft.channel == "linkedin"
    assert draft.requires_human_review is True
    assert "Nimbus" in draft.body
    assert any("Shipped retrieval ranking" in point for point in draft.talking_points)


def test_no_network_calls() -> None:
    """Generator never performs HTTP calls."""

    with (
        patch("httpx.Client", MagicMock()) as client_cls,
        patch("httpx.AsyncClient", MagicMock()) as async_cls,
        patch("httpx.get", MagicMock()) as get_fn,
        patch("httpx.post", MagicMock()) as post_fn,
    ):
        RecruiterOutreachDraftService().generate(
            company="Globex",
            role="SRE",
            channel="email",
        )
        client_cls.assert_not_called()
        async_cls.assert_not_called()
        get_fn.assert_not_called()
        post_fn.assert_not_called()


def test_deterministic() -> None:
    """Repeated generate calls are identical."""

    service = RecruiterOutreachDraftService()
    kwargs = {
        "company": "Acme",
        "role": "SWE",
        "recruiter_name": "Sam",
        "channel": "email",
        "notes": "Python + K8s",
    }
    assert service.generate(**kwargs) == service.generate(**kwargs)

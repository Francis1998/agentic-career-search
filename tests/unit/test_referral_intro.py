"""Unit tests for ReferralIntroDraftService."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from autoapply_agent.services.referral_intro import ReferralIntroDraftService

if TYPE_CHECKING:
    from _pytest.capture import CaptureFixture
    from _pytest.fixtures import FixtureRequest
    from _pytest.logging import LogCaptureFixture
    from _pytest.monkeypatch import MonkeyPatch
    from pytest_mock.plugin import MockerFixture


def test_empty_company_raises() -> None:
    """Blank company name raises ValueError."""

    with pytest.raises(ValueError, match="company"):
        ReferralIntroDraftService().generate(
            company=" ",
            role="SWE",
            connector_name="Sam",
            mutual_context="Same alumni network",
        )


def test_empty_connector_raises() -> None:
    """Blank connector_name raises ValueError."""

    with pytest.raises(ValueError, match="connector_name"):
        ReferralIntroDraftService().generate(
            company="Acme",
            role="SWE",
            connector_name="  ",
            mutual_context="Same alumni network",
        )


def test_empty_mutual_context_raises() -> None:
    """Blank mutual_context raises ValueError."""

    with pytest.raises(ValueError, match="mutual_context"):
        ReferralIntroDraftService().generate(
            company="Acme",
            role="SWE",
            connector_name="Sam",
            mutual_context="",
        )


def test_invalid_channel_raises() -> None:
    """Unsupported channel raises ValueError."""

    with pytest.raises(ValueError, match="channel"):
        ReferralIntroDraftService().generate(
            company="Acme",
            role="SWE",
            connector_name="Sam",
            mutual_context="Same lab",
            channel="sms",
        )


def test_draft_always_requires_human_review() -> None:
    """Every draft flags requires_human_review=True and never auto-sends."""

    draft = ReferralIntroDraftService().generate(
        company="Acme",
        role="Platform Engineer",
        connector_name="Alex",
        mutual_context="worked together on infra on-call",
    )
    assert draft.requires_human_review is True
    assert draft.channel == "email"
    assert "Acme" in draft.subject
    assert "Alex" in draft.body
    assert "do not auto-send" in draft.body.lower()
    assert draft.talking_points


def test_linkedin_channel_draft() -> None:
    """LinkedIn channel produces a DM-style body."""

    draft = ReferralIntroDraftService().generate(
        company="Nimbus",
        role="ML Engineer",
        connector_name="Jordan",
        mutual_context="same ML reading group",
        channel="linkedin",
    )
    assert draft.channel == "linkedin"
    assert "Nimbus" in draft.body
    assert "Jordan" in draft.body


def test_no_network_calls() -> None:
    """Generator never performs HTTP calls."""

    with (
        patch("httpx.Client", MagicMock()) as client_cls,
        patch("httpx.AsyncClient", MagicMock()) as async_cls,
        patch("httpx.get", MagicMock()) as get_fn,
        patch("httpx.post", MagicMock()) as post_fn,
    ):
        ReferralIntroDraftService().generate(
            company="Globex",
            role="SRE",
            connector_name="Sam",
            mutual_context="prior coworker",
        )
        client_cls.assert_not_called()
        async_cls.assert_not_called()
        get_fn.assert_not_called()
        post_fn.assert_not_called()


def test_deterministic() -> None:
    """Repeated generate calls are identical."""

    service = ReferralIntroDraftService()
    kwargs = {
        "company": "Acme",
        "role": "SWE",
        "connector_name": "Sam",
        "mutual_context": "alumni",
        "channel": "email",
    }
    assert service.generate(**kwargs) == service.generate(**kwargs)

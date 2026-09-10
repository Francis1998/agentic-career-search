"""Unit tests for InterviewFeedbackSynthesizer."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from autoapply_agent.services.interview_feedback import InterviewFeedbackSynthesizer

if TYPE_CHECKING:
    from _pytest.capture import CaptureFixture
    from _pytest.fixtures import FixtureRequest
    from _pytest.logging import LogCaptureFixture
    from _pytest.monkeypatch import MonkeyPatch
    from pytest_mock.plugin import MockerFixture


def test_empty_company_raises() -> None:
    """Blank company name raises ValueError."""

    with pytest.raises(ValueError, match="company"):
        InterviewFeedbackSynthesizer().synthesize(
            company="  ",
            role="SWE",
            notes="Talked about systems design",
        )


def test_empty_notes_raises() -> None:
    """Blank notes raise ValueError."""

    with pytest.raises(ValueError, match="notes"):
        InterviewFeedbackSynthesizer().synthesize(
            company="Acme",
            role="SWE",
            notes="   ",
        )


def test_invalid_outcome_raises() -> None:
    """Unsupported outcome_signal raises ValueError."""

    with pytest.raises(ValueError, match="outcome_signal"):
        InterviewFeedbackSynthesizer().synthesize(
            company="Acme",
            role="SWE",
            notes="Good system design round",
            outcome_signal="maybe",
        )


def test_brief_always_requires_human_review() -> None:
    """Every brief flags requires_human_review=True and never auto-sends."""

    brief = InterviewFeedbackSynthesizer().synthesize(
        company="Acme",
        role="Platform Engineer",
        notes="Strong ownership story; deferred on on-call details",
        outcome_signal="mixed",
    )
    assert brief.requires_human_review is True
    assert brief.company == "Acme"
    assert brief.role == "Platform Engineer"
    assert brief.outcome_signal == "mixed"
    assert brief.strengths
    assert brief.gaps
    assert any("do not auto-send" in item.lower() for item in brief.follow_ups)
    assert any("recovery" in item.lower() for item in brief.gaps)


def test_positive_outcome_adds_negotiation_follow_up() -> None:
    """Positive outcome adds negotiation prep follow-up."""

    brief = InterviewFeedbackSynthesizer().synthesize(
        company="Nimbus",
        role="ML Engineer",
        notes="Hiring manager liked retrieval ranking impact narrative in detail",
        outcome_signal="positive",
    )
    assert brief.outcome_signal == "positive"
    assert any("negotiation" in item.lower() for item in brief.follow_ups)


def test_no_network_calls() -> None:
    """Synthesizer never performs HTTP calls."""

    with (
        patch("httpx.Client", MagicMock()) as client_cls,
        patch("httpx.AsyncClient", MagicMock()) as async_cls,
        patch("httpx.get", MagicMock()) as get_fn,
        patch("httpx.post", MagicMock()) as post_fn,
    ):
        InterviewFeedbackSynthesizer().synthesize(
            company="Globex",
            role="SRE",
            notes="Discussed incident response",
        )
        client_cls.assert_not_called()
        async_cls.assert_not_called()
        get_fn.assert_not_called()
        post_fn.assert_not_called()


def test_deterministic() -> None:
    """Repeated synthesize calls are identical."""

    service = InterviewFeedbackSynthesizer()
    kwargs = {
        "company": "Acme",
        "role": "SWE",
        "notes": "Solid coding round with clear communication",
        "outcome_signal": "positive",
    }
    assert service.synthesize(**kwargs) == service.synthesize(**kwargs)

"""Unit tests for InterviewDebriefChecklist."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from autoapply_agent.services.interview_debrief import InterviewDebriefChecklist

if TYPE_CHECKING:
    from _pytest.capture import CaptureFixture
    from _pytest.fixtures import FixtureRequest
    from _pytest.logging import LogCaptureFixture
    from _pytest.monkeypatch import MonkeyPatch
    from pytest_mock.plugin import MockerFixture


def test_blank_company_raises() -> None:
    """Blank company raises ValueError."""

    with pytest.raises(ValueError, match="company"):
        InterviewDebriefChecklist().build(
            company=" ",
            role="Backend Engineer",
            what_went_well=["Clear system design"],
        )


def test_blank_role_raises() -> None:
    """Blank role raises ValueError."""

    with pytest.raises(ValueError, match="role"):
        InterviewDebriefChecklist().build(
            company="Acme",
            role="",
            what_went_well=["Clear system design"],
        )


def test_builds_checklist_from_structured_inputs() -> None:
    """Structured went-well / gaps / follow-ups become an ordered HITL checklist."""

    plan = InterviewDebriefChecklist().build(
        company="Acme",
        role="Backend Engineer",
        what_went_well=["Clear system design", "Strong Python depth"],
        gaps=["Weak concurrency story"],
        follow_ups=["Send architecture sketch", "Ask about on-call"],
    )
    assert plan.company == "Acme"
    assert plan.role == "Backend Engineer"
    assert plan.what_went_well == ["Clear system design", "Strong Python depth"]
    assert plan.gaps == ["Weak concurrency story"]
    assert "Send architecture sketch" in plan.follow_ups
    assert plan.checklist
    assert any("went well" in item.lower() or "strength" in item.lower() for item in plan.checklist)
    assert any("gap" in item.lower() for item in plan.checklist)
    assert any("follow" in item.lower() for item in plan.checklist)


def test_empty_sections_still_emit_guidance_checklist() -> None:
    """Missing optional lists still yield a minimal human-review checklist."""

    plan = InterviewDebriefChecklist().build(
        company="Acme",
        role="SRE",
    )
    assert plan.what_went_well == []
    assert plan.gaps == []
    assert plan.follow_ups == []
    assert plan.checklist
    assert plan.guidance


def test_never_auto_submits_requires_human_review() -> None:
    """Every payload flags HITL review and never auto-submits notes."""

    plan = InterviewDebriefChecklist().build(
        company="Acme",
        role="PM",
        what_went_well=["Stakeholder clarity"],
        gaps=["Metrics framing"],
        follow_ups=["Share product brief"],
    )
    assert plan.requires_human_review is True
    assert plan.auto_submit is False


def test_no_network_calls() -> None:
    """Checklist builder never performs HTTP calls."""

    with (
        patch("httpx.Client", MagicMock()) as client_cls,
        patch("httpx.AsyncClient", MagicMock()) as async_cls,
        patch("httpx.get", MagicMock()) as get_fn,
        patch("httpx.post", MagicMock()) as post_fn,
    ):
        InterviewDebriefChecklist().build(
            company="Acme",
            role="Data Engineer",
            what_went_well=["SQL fluency"],
        )
        client_cls.assert_not_called()
        async_cls.assert_not_called()
        get_fn.assert_not_called()
        post_fn.assert_not_called()

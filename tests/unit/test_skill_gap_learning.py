"""Unit tests for SkillGapLearningPathPlanner."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from autoapply_agent.services.skill_gap_learning import SkillGapLearningPathPlanner

if TYPE_CHECKING:
    from _pytest.capture import CaptureFixture
    from _pytest.fixtures import FixtureRequest
    from _pytest.logging import LogCaptureFixture
    from _pytest.monkeypatch import MonkeyPatch
    from pytest_mock.plugin import MockerFixture


def test_empty_required_skills_raises() -> None:
    """Empty required_skills raises ValueError."""

    with pytest.raises(ValueError, match="required_skills"):
        SkillGapLearningPathPlanner().plan(
            have_skills=["python"],
            required_skills=[],
        )


def test_blank_required_skill_tokens_raise() -> None:
    """Whitespace-only required skills raise ValueError."""

    with pytest.raises(ValueError, match="required_skills"):
        SkillGapLearningPathPlanner().plan(
            have_skills=["python"],
            required_skills=["  ", ""],
        )


def test_orders_milestones_for_missing_skills() -> None:
    """Missing skills become ordered learning milestones; have skills are skipped."""

    path = SkillGapLearningPathPlanner().plan(
        have_skills=["Python", "SQL"],
        required_skills=["python", "kubernetes", "SQL", "system design"],
        role="Backend Engineer",
    )
    assert path.missing_skills == ["kubernetes", "system design"]
    assert path.have_skills == ["Python", "SQL"]
    assert len(path.milestones) == 2
    assert "kubernetes" in path.milestones[0].lower()
    assert "system design" in path.milestones[1].lower()
    assert path.guidance


def test_no_gaps_emits_maintain_guidance() -> None:
    """When all required skills are present, milestones are empty and guidance says maintain."""

    path = SkillGapLearningPathPlanner().plan(
        have_skills=["python", "go"],
        required_skills=["Python", "Go"],
    )
    assert path.missing_skills == []
    assert path.milestones == []
    assert any("maintain" in line.lower() or "no gap" in line.lower() for line in path.guidance)


def test_never_enrolls_requires_human_review() -> None:
    """Every payload flags HITL review and never auto-enrolls courses."""

    path = SkillGapLearningPathPlanner().plan(
        have_skills=["git"],
        required_skills=["git", "terraform"],
    )
    assert path.requires_human_review is True
    assert path.auto_enroll is False


def test_no_network_calls() -> None:
    """Planner never performs HTTP calls."""

    with (
        patch("httpx.Client", MagicMock()) as client_cls,
        patch("httpx.AsyncClient", MagicMock()) as async_cls,
        patch("httpx.get", MagicMock()) as get_fn,
        patch("httpx.post", MagicMock()) as post_fn,
    ):
        SkillGapLearningPathPlanner().plan(
            have_skills=["python"],
            required_skills=["python", "rust"],
        )
        client_cls.assert_not_called()
        async_cls.assert_not_called()
        get_fn.assert_not_called()
        post_fn.assert_not_called()

"""Unit tests for StarBehavioralStoryMatcher."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from autoapply_agent.services.star_story import StarBehavioralStoryMatcher, StarStory


def test_blank_jd_raises() -> None:
    """Blank job_description raises ValueError."""

    with pytest.raises(ValueError, match="job_description"):
        StarBehavioralStoryMatcher().match("  ", [])


def test_low_top_k_raises() -> None:
    """top_k below 1 raises ValueError."""

    with pytest.raises(ValueError, match="top_k"):
        StarBehavioralStoryMatcher().match("Python lead role", [], top_k=0)


def test_matches_leadership_story() -> None:
    """Leadership JD cues match a tagged leadership STAR story."""

    stories = [
        StarStory(
            story_id="s1",
            situation="Team missed a milestone",
            task="Restore delivery confidence",
            action="Mentored two engineers and drove a weekly stakeholder sync",
            result="Shipped on time with zero Sev-1 incidents",
            tags=("leadership", "delivery"),
        )
    ]
    plan = StarBehavioralStoryMatcher().match(
        "Lead a cross-functional squad and mentor engineers on AWS.",
        stories,
    )
    assert plan.requires_human_review is True
    assert plan.auto_send is False
    assert plan.matches
    assert plan.matches[0].competency == "leadership"
    assert plan.matches[0].score > 0


def test_uncovered_when_bank_empty() -> None:
    """Empty story bank leaves competencies uncovered."""

    plan = StarBehavioralStoryMatcher().match(
        "Own on-call incident response and postmortems.",
        [],
    )
    assert "incident" in plan.uncovered_competencies
    assert plan.matches == []


def test_no_network_calls() -> None:
    """Matcher never performs HTTP calls."""

    with (
        patch("httpx.Client", MagicMock()) as client_cls,
        patch("httpx.AsyncClient", MagicMock()) as async_cls,
        patch("httpx.get", MagicMock()) as get_fn,
        patch("httpx.post", MagicMock()) as post_fn,
    ):
        StarBehavioralStoryMatcher().match("Deadline delivery lead role", [])
        client_cls.assert_not_called()
        async_cls.assert_not_called()
        get_fn.assert_not_called()
        post_fn.assert_not_called()

"""Unit tests for PhoneScreenAgendaPlanner."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from autoapply_agent.services.phone_screen_agenda import PhoneScreenAgendaPlanner


def test_blank_jd_raises() -> None:
    """Blank job_description raises ValueError."""

    with pytest.raises(ValueError, match="job_description"):
        PhoneScreenAgendaPlanner().plan("  ")


def test_low_target_minutes_raises() -> None:
    """target_minutes below 10 raises ValueError."""

    with pytest.raises(ValueError, match="target_minutes"):
        PhoneScreenAgendaPlanner().plan("Python engineer role", target_minutes=5)


def test_stack_and_closing_items() -> None:
    """JD stack cues produce stack_depth plus candidate_questions."""

    plan = PhoneScreenAgendaPlanner().plan(
        "You will own Python services on AWS with cross-functional stakeholders."
    )
    topics = {item.topic for item in plan.items}
    assert "stack_depth" in topics
    assert "collaboration" in topics
    assert "candidate_questions" in topics
    assert plan.requires_human_review is True
    assert plan.auto_book is False


def test_no_network_calls() -> None:
    """Planner never performs HTTP calls."""

    with (
        patch("httpx.Client", MagicMock()) as client_cls,
        patch("httpx.AsyncClient", MagicMock()) as async_cls,
        patch("httpx.get", MagicMock()) as get_fn,
        patch("httpx.post", MagicMock()) as post_fn,
    ):
        PhoneScreenAgendaPlanner().plan("Remote hybrid compensation discussion")
        client_cls.assert_not_called()
        async_cls.assert_not_called()
        get_fn.assert_not_called()
        post_fn.assert_not_called()

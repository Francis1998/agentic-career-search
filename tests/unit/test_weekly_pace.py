"""Unit tests for WeeklyApplicationPaceAdvisor."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from autoapply_agent.services.weekly_pace import WeeklyApplicationPaceAdvisor

if TYPE_CHECKING:
    from _pytest.capture import CaptureFixture
    from _pytest.fixtures import FixtureRequest
    from _pytest.logging import LogCaptureFixture
    from _pytest.monkeypatch import MonkeyPatch
    from pytest_mock.plugin import MockerFixture


def test_empty_week_label_raises() -> None:
    """Blank week_label raises ValueError."""

    with pytest.raises(ValueError, match="week_label"):
        WeeklyApplicationPaceAdvisor().advise(
            week_label=" ",
            planned_applications=5,
        )


def test_negative_planned_raises() -> None:
    """Negative planned_applications raises ValueError."""

    with pytest.raises(ValueError, match="planned_applications"):
        WeeklyApplicationPaceAdvisor().advise(
            week_label="2026-W37",
            planned_applications=-1,
        )


def test_bad_target_raises() -> None:
    """target_applications < 1 raises ValueError."""

    with pytest.raises(ValueError, match="target_applications"):
        WeeklyApplicationPaceAdvisor().advise(
            week_label="2026-W37",
            planned_applications=5,
            target_applications=0,
        )


def test_under_pace_band() -> None:
    """Ratio under 0.5 maps to under_pace."""

    advice = WeeklyApplicationPaceAdvisor().advise(
        week_label="2026-W37",
        planned_applications=2,
        target_applications=10,
    )
    assert advice.band == "under_pace"
    assert advice.pace_ratio == 0.2


def test_on_pace_band() -> None:
    """Ratio in [0.5, 1.25] maps to on_pace."""

    advice = WeeklyApplicationPaceAdvisor().advise(
        week_label="2026-W37",
        planned_applications=10,
        target_applications=10,
    )
    assert advice.band == "on_pace"


def test_hot_band() -> None:
    """Ratio in (1.25, 1.75] maps to hot."""

    advice = WeeklyApplicationPaceAdvisor().advise(
        week_label="2026-W37",
        planned_applications=15,
        target_applications=10,
    )
    assert advice.band == "hot"


def test_overload_band() -> None:
    """Ratio above 1.75 maps to overload."""

    advice = WeeklyApplicationPaceAdvisor().advise(
        week_label="2026-W37",
        planned_applications=20,
        target_applications=10,
    )
    assert advice.band == "overload"


def test_never_auto_submits_requires_human_review() -> None:
    """Every payload flags HITL review and never auto-submits."""

    advice = WeeklyApplicationPaceAdvisor().advise(
        week_label="2026-W37",
        planned_applications=8,
        target_applications=10,
    )
    assert advice.requires_human_review is True
    assert advice.auto_submit is False
    assert advice.guidance


def test_no_network_calls() -> None:
    """Advisor never performs HTTP calls."""

    with (
        patch("httpx.Client", MagicMock()) as client_cls,
        patch("httpx.AsyncClient", MagicMock()) as async_cls,
        patch("httpx.get", MagicMock()) as get_fn,
        patch("httpx.post", MagicMock()) as post_fn,
    ):
        WeeklyApplicationPaceAdvisor().advise(
            week_label="2026-W37",
            planned_applications=5,
        )
        client_cls.assert_not_called()
        async_cls.assert_not_called()
        get_fn.assert_not_called()
        post_fn.assert_not_called()

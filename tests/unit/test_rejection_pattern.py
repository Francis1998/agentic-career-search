"""Unit tests for RejectionPatternAnalyzer."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from autoapply_agent.services.rejection_pattern import RejectionPatternAnalyzer

if TYPE_CHECKING:
    from _pytest.capture import CaptureFixture
    from _pytest.fixtures import FixtureRequest
    from _pytest.logging import LogCaptureFixture
    from _pytest.monkeypatch import MonkeyPatch
    from pytest_mock.plugin import MockerFixture


def test_empty_reasons_raises() -> None:
    """Empty reasons raise ValueError."""

    with pytest.raises(ValueError, match="reasons"):
        RejectionPatternAnalyzer().analyze([])


def test_blank_reasons_raise() -> None:
    """Whitespace-only reasons raise ValueError."""

    with pytest.raises(ValueError, match="reasons"):
        RejectionPatternAnalyzer().analyze([" ", ""])


def test_clusters_known_themes() -> None:
    """Known cue phrases map into themed buckets with actions."""

    report = RejectionPatternAnalyzer().analyze(
        [
            "Need more senior experience",
            "Missing Kubernetes skills",
            "Role filled by another candidate",
            "Team fit concerns on communication",
        ]
    )
    theme_names = {item.theme for item in report.themes}
    assert "experience_depth" in theme_names
    assert "skills_mismatch" in theme_names
    assert "timing_headcount" in theme_names
    assert "process_fit" in theme_names
    assert all(item.count >= 1 for item in report.themes)
    assert all(item.suggested_action for item in report.themes)


def test_uncategorized_preserved() -> None:
    """Unknown notes stay in uncategorized for HITL review."""

    report = RejectionPatternAnalyzer().analyze(["Opaque decision, no details"])
    assert report.themes == []
    assert report.uncategorized == ["Opaque decision, no details"]


def test_never_auto_rewrites_requires_human_review() -> None:
    """Every payload flags HITL review and never auto-rewrites."""

    report = RejectionPatternAnalyzer().analyze(["Missing SQL skill"])
    assert report.requires_human_review is True
    assert report.auto_rewrite is False


def test_no_network_calls() -> None:
    """Analyzer never performs HTTP calls."""

    with (
        patch("httpx.Client", MagicMock()) as client_cls,
        patch("httpx.AsyncClient", MagicMock()) as async_cls,
        patch("httpx.get", MagicMock()) as get_fn,
        patch("httpx.post", MagicMock()) as post_fn,
    ):
        RejectionPatternAnalyzer().analyze(["Need more years of experience"])
        client_cls.assert_not_called()
        async_cls.assert_not_called()
        get_fn.assert_not_called()
        post_fn.assert_not_called()

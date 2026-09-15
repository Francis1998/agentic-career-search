"""Unit tests for ResumeBulletImpactScorer."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from autoapply_agent.services.bullet_impact import ResumeBulletImpactScorer

if TYPE_CHECKING:
    from _pytest.capture import CaptureFixture
    from _pytest.fixtures import FixtureRequest
    from _pytest.logging import LogCaptureFixture
    from _pytest.monkeypatch import MonkeyPatch
    from pytest_mock.plugin import MockerFixture


def test_empty_bullets_raise() -> None:
    """Empty bullet list raises ValueError."""

    with pytest.raises(ValueError, match="bullets"):
        ResumeBulletImpactScorer().score([])


def test_strong_quantified_bullet() -> None:
    """Bullets with %/$/scale score in the strong band."""

    report = ResumeBulletImpactScorer().score(
        ["Led migration that cut latency 40% and saved $1.2M for 2M users."]
    )
    assert report.bullets_scored[0].band == "strong"
    assert report.bullets_scored[0].score >= 0.75
    assert "percent" in report.bullets_scored[0].cues
    assert "money" in report.bullets_scored[0].cues


def test_weak_bullet_without_metrics() -> None:
    """Adjective-only bullets land in the weak band."""

    report = ResumeBulletImpactScorer().score(
        ["Responsible for various backend tasks and helped the team."]
    )
    assert report.bullets_scored[0].band == "weak"
    assert report.weak_bullets


def test_never_auto_rewrites() -> None:
    """Scorer never auto-rewrites and always requires human review."""

    report = ResumeBulletImpactScorer().score(["Shipped feature used by 10k customers."])
    assert report.requires_human_review is True
    assert report.auto_rewrite is False


def test_no_network_calls() -> None:
    """Scorer never performs HTTP calls."""

    with (
        patch("httpx.Client", MagicMock()) as client_cls,
        patch("httpx.AsyncClient", MagicMock()) as async_cls,
        patch("httpx.get", MagicMock()) as get_fn,
        patch("httpx.post", MagicMock()) as post_fn,
    ):
        ResumeBulletImpactScorer().score(["Improved throughput 3x."])
        client_cls.assert_not_called()
        async_cls.assert_not_called()
        get_fn.assert_not_called()
        post_fn.assert_not_called()

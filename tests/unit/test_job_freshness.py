"""Unit tests for JobPostingFreshnessScorer."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from autoapply_agent.services.job_freshness import JobPostingFreshnessScorer

if TYPE_CHECKING:
    from _pytest.capture import CaptureFixture
    from _pytest.fixtures import FixtureRequest
    from _pytest.logging import LogCaptureFixture
    from _pytest.monkeypatch import MonkeyPatch
    from pytest_mock.plugin import MockerFixture


def test_negative_age_raises() -> None:
    """Negative age_days raises ValueError."""

    with pytest.raises(ValueError, match="age_days"):
        JobPostingFreshnessScorer().score(age_days=-1)


def test_fresh_band() -> None:
    """age_days 0-7 maps to fresh."""

    advice = JobPostingFreshnessScorer().score(age_days=3, title="SWE", company="Acme")
    assert advice.band == "fresh"
    assert advice.age_days == 3
    assert 0.0 <= advice.freshness_score <= 1.0
    assert advice.freshness_score >= 0.75


def test_aging_band() -> None:
    """age_days 8-21 maps to aging."""

    advice = JobPostingFreshnessScorer().score(age_days=14)
    assert advice.band == "aging"
    assert 0.4 <= advice.freshness_score < 0.75


def test_stale_band() -> None:
    """age_days 22-45 maps to stale."""

    advice = JobPostingFreshnessScorer().score(age_days=30)
    assert advice.band == "stale"
    assert 0.15 <= advice.freshness_score < 0.4


def test_expired_band() -> None:
    """age_days 46+ maps to expired."""

    advice = JobPostingFreshnessScorer().score(age_days=60)
    assert advice.band == "expired"
    assert advice.freshness_score < 0.15


def test_boundary_days() -> None:
    """Band edges at 7/21/45 are inclusive on the upper side of each band."""

    assert JobPostingFreshnessScorer().score(age_days=0).band == "fresh"
    assert JobPostingFreshnessScorer().score(age_days=7).band == "fresh"
    assert JobPostingFreshnessScorer().score(age_days=8).band == "aging"
    assert JobPostingFreshnessScorer().score(age_days=21).band == "aging"
    assert JobPostingFreshnessScorer().score(age_days=22).band == "stale"
    assert JobPostingFreshnessScorer().score(age_days=45).band == "stale"
    assert JobPostingFreshnessScorer().score(age_days=46).band == "expired"


def test_never_auto_applies_requires_human_review() -> None:
    """Every payload flags HITL review and never auto-applies."""

    advice = JobPostingFreshnessScorer().score(age_days=10, title="ML Eng")
    assert advice.requires_human_review is True
    assert advice.auto_apply is False
    assert advice.guidance


def test_no_network_calls() -> None:
    """Scorer never performs HTTP calls."""

    with (
        patch("httpx.Client", MagicMock()) as client_cls,
        patch("httpx.AsyncClient", MagicMock()) as async_cls,
        patch("httpx.get", MagicMock()) as get_fn,
        patch("httpx.post", MagicMock()) as post_fn,
    ):
        JobPostingFreshnessScorer().score(age_days=5)
        client_cls.assert_not_called()
        async_cls.assert_not_called()
        get_fn.assert_not_called()
        post_fn.assert_not_called()

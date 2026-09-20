"""Unit tests for NonCompeteRestrictivenessFlagger."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from autoapply_agent.services.noncompete_flagger import NonCompeteRestrictivenessFlagger


def test_highly_restrictive_long_duration() -> None:
    """24-month worldwide non-compete is highly_restrictive."""

    report = NonCompeteRestrictivenessFlagger().flag(
        "Employee agrees to a non-compete for 24 months worldwide."
    )
    assert report.restrictiveness_band == "highly_restrictive"
    assert report.duration_months == 24
    assert report.auto_accept is False
    assert report.requires_human_review is True


def test_mildly_restrictive() -> None:
    """Bare non-compete mention without duration is mildly_restrictive."""

    report = NonCompeteRestrictivenessFlagger().flag(
        "This offer includes a non-compete clause subject to local law."
    )
    assert report.restrictiveness_band == "mildly_restrictive"


def test_none_detected() -> None:
    """Neutral offer text yields none_detected."""

    report = NonCompeteRestrictivenessFlagger().flag(
        "Start date is October 1. Benefits begin day one."
    )
    assert report.restrictiveness_band == "none_detected"


def test_garden_leave_cue() -> None:
    """Garden leave is flagged when present."""

    report = NonCompeteRestrictivenessFlagger().flag(
        "A 6 month non-compete with garden leave applies."
    )
    assert report.has_garden_leave is True
    assert report.duration_months == 6


def test_empty_text_raises() -> None:
    """Empty text raises ValueError."""

    with pytest.raises(ValueError, match="text"):
        NonCompeteRestrictivenessFlagger().flag("   ")


def test_no_network_calls() -> None:
    """Flagger never performs HTTP calls."""

    with (
        patch("httpx.Client", MagicMock()) as client_cls,
        patch("httpx.AsyncClient", MagicMock()) as async_cls,
        patch("httpx.get", MagicMock()) as get_fn,
        patch("httpx.post", MagicMock()) as post_fn,
    ):
        NonCompeteRestrictivenessFlagger().flag("non-compete for 12 months")
        client_cls.assert_not_called()
        async_cls.assert_not_called()
        get_fn.assert_not_called()
        post_fn.assert_not_called()

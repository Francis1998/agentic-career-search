"""Unit tests for GhostJobSignalFlagger."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from autoapply_agent.services.ghost_job import GhostJobSignalFlagger


def test_blank_jd_raises() -> None:
    """Blank job_description raises ValueError."""

    with pytest.raises(ValueError, match="job_description"):
        GhostJobSignalFlagger().flag("  ")


def test_evergreen_raises_risk() -> None:
    """Evergreen language yields medium/high risk band."""

    report = GhostJobSignalFlagger().flag(
        "We are always hiring on a rolling basis for our talent community."
    )
    kinds = {signal.kind for signal in report.signals}
    assert "evergreen_language" in kinds
    assert report.auto_apply is False
    assert report.requires_human_review is True
    assert report.risk_band in {"low", "medium", "high"}
    assert report.risk_score > 0


def test_salary_band_skips_missing_comp() -> None:
    """has_salary_band=True suppresses missing_comp cue."""

    report = GhostJobSignalFlagger().flag(
        "Competitive salary DOE for backend engineers.",
        has_salary_band=True,
    )
    kinds = {signal.kind for signal in report.signals}
    assert "missing_comp" not in kinds


def test_clear_when_concrete() -> None:
    """Concrete JD without ghost cues bands as clear."""

    report = GhostJobSignalFlagger().flag(
        "Hiring one Senior Backend Engineer reporting to Alice, req #4421, $180k-$200k.",
        has_salary_band=True,
    )
    assert report.risk_band == "clear"
    assert report.signals == []


def test_no_network_calls() -> None:
    """Flagger never performs HTTP calls."""

    with (
        patch("httpx.Client", MagicMock()) as client_cls,
        patch("httpx.AsyncClient", MagicMock()) as async_cls,
        patch("httpx.get", MagicMock()) as get_fn,
        patch("httpx.post", MagicMock()) as post_fn,
    ):
        GhostJobSignalFlagger().flag("Always hiring evergreen backend role")
        client_cls.assert_not_called()
        async_cls.assert_not_called()
        get_fn.assert_not_called()
        post_fn.assert_not_called()

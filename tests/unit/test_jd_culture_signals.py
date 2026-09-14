"""Unit tests for JdCultureSignalExtractor."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from autoapply_agent.services.jd_culture_signals import JdCultureSignalExtractor

if TYPE_CHECKING:
    from _pytest.capture import CaptureFixture
    from _pytest.fixtures import FixtureRequest
    from _pytest.logging import LogCaptureFixture
    from _pytest.monkeypatch import MonkeyPatch
    from pytest_mock.plugin import MockerFixture


def test_blank_company_raises() -> None:
    """Blank company raises ValueError."""

    with pytest.raises(ValueError, match="company"):
        JdCultureSignalExtractor().extract(
            company=" ",
            role="Backend Engineer",
            jd_text="Fast-paced team with on-call.",
        )


def test_blank_jd_raises() -> None:
    """Blank jd_text raises ValueError."""

    with pytest.raises(ValueError, match="jd_text"):
        JdCultureSignalExtractor().extract(
            company="Acme",
            role="Backend Engineer",
            jd_text="",
        )


def test_extracts_known_signals() -> None:
    """Known culture phrases become typed signals with evidence."""

    report = JdCultureSignalExtractor().extract(
        company="Acme",
        role="Backend Engineer",
        jd_text=(
            "Join a fast-paced team with weekly stand-ups, cross-functional "
            "collaboration, and rotating on-call."
        ),
    )
    names = {item.signal for item in report.signals}
    assert "fast_pace" in names
    assert "oncall" in names
    assert "collaboration" in names
    assert "meeting_load" in names
    assert all(item.evidence for item in report.signals)


def test_no_signals_still_emits_guidance() -> None:
    """Unmatched JD text still yields HITL guidance."""

    report = JdCultureSignalExtractor().extract(
        company="Acme",
        role="Analyst",
        jd_text="Write reports and maintain spreadsheets.",
    )
    assert report.signals == []
    assert report.guidance


def test_never_auto_applies_requires_human_review() -> None:
    """Every payload flags HITL review and never auto-applies."""

    report = JdCultureSignalExtractor().extract(
        company="Acme",
        role="SRE",
        jd_text="Pager rotation and incident response ownership.",
    )
    assert report.requires_human_review is True
    assert report.auto_apply is False


def test_no_network_calls() -> None:
    """Extractor never performs HTTP calls."""

    with (
        patch("httpx.Client", MagicMock()) as client_cls,
        patch("httpx.AsyncClient", MagicMock()) as async_cls,
        patch("httpx.get", MagicMock()) as get_fn,
        patch("httpx.post", MagicMock()) as post_fn,
    ):
        JdCultureSignalExtractor().extract(
            company="Acme",
            role="PM",
            jd_text="Autonomy and ownership expected.",
        )
        client_cls.assert_not_called()
        async_cls.assert_not_called()
        get_fn.assert_not_called()
        post_fn.assert_not_called()

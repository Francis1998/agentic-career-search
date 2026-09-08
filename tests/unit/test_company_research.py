"""Unit tests for CompanyResearchBriefService."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from autoapply_agent.services.company_research import CompanyResearchBriefService

if TYPE_CHECKING:
    from _pytest.capture import CaptureFixture
    from _pytest.fixtures import FixtureRequest
    from _pytest.logging import LogCaptureFixture
    from _pytest.monkeypatch import MonkeyPatch
    from pytest_mock.plugin import MockerFixture


def test_empty_company_raises() -> None:
    """Blank company name raises ValueError."""

    with pytest.raises(ValueError, match="company"):
        CompanyResearchBriefService().generate(company="  ")


def test_brief_always_requires_human_review() -> None:
    """Every brief flags requires_human_review=True."""

    brief = CompanyResearchBriefService().generate(company="Acme")
    assert brief.requires_human_review is True
    assert brief.company == "Acme"
    assert brief.talking_points
    assert brief.open_questions


def test_jd_signals_extracted() -> None:
    """Known domain tokens from JD become jd_signals."""

    brief = CompanyResearchBriefService().generate(
        company="Nimbus",
        job_title="ML Engineer",
        job_text="Remote AI fintech platform hiring ML engineers",
    )
    assert any("remote" in signal.lower() for signal in brief.jd_signals)
    assert any("fintech" in signal.lower() or "ai" in signal.lower() for signal in brief.jd_signals)
    assert "ML Engineer" in brief.one_liner


def test_no_network_calls() -> None:
    """Generator never performs HTTP calls."""

    with (
        patch("httpx.Client", MagicMock()) as client_cls,
        patch("httpx.AsyncClient", MagicMock()) as async_cls,
        patch("httpx.get", MagicMock()) as get_fn,
        patch("httpx.post", MagicMock()) as post_fn,
    ):
        CompanyResearchBriefService().generate(
            company="Globex",
            job_text="Enterprise B2B security startup",
        )
        client_cls.assert_not_called()
        async_cls.assert_not_called()
        get_fn.assert_not_called()
        post_fn.assert_not_called()


def test_deterministic() -> None:
    """Repeated generate calls are identical."""

    service = CompanyResearchBriefService()
    kwargs = {"company": "Acme", "job_title": "SWE", "job_text": "hybrid python role"}
    assert service.generate(**kwargs) == service.generate(**kwargs)


def test_title_influences_talking_points() -> None:
    """Job title is reflected in talking points."""

    brief = CompanyResearchBriefService().generate(
        company="Acme",
        job_title="Staff Platform Engineer",
    )
    assert any("Staff Platform Engineer" in point for point in brief.talking_points)

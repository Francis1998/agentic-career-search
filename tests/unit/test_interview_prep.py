"""Unit tests for InterviewPrepBriefService (HITL assistive only)."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import httpx

from autoapply_agent.services.interview_prep import InterviewPrepBriefService

if TYPE_CHECKING:
    from _pytest.capture import CaptureFixture
    from _pytest.fixtures import FixtureRequest
    from _pytest.logging import LogCaptureFixture
    from _pytest.monkeypatch import MonkeyPatch
    from pytest_mock.plugin import MockerFixture


def test_generate_brief_includes_questions_and_star_prompts() -> None:
    """Briefs include likely questions and STAR prompts for the target role."""

    service = InterviewPrepBriefService()
    brief = service.generate(
        job_title="Senior Backend Engineer",
        company="Acme Labs",
        job_text="Build FastAPI services on AWS with strong Python skills.",
        candidate_skills=["python"],
    )

    assert brief.job_title == "Senior Backend Engineer"
    assert brief.company == "Acme Labs"
    assert len(brief.likely_questions) >= 4
    assert any("Acme Labs" in q for q in brief.likely_questions)
    assert len(brief.star_prompts) >= 4
    assert brief.requires_human_review is True
    assert any("fastapi" in gap.lower() or "aws" in gap.lower() for gap in brief.focus_gaps)


def test_generate_brief_handles_missing_optional_fields() -> None:
    """Missing company/job text still yields a usable HITL brief."""

    service = InterviewPrepBriefService()
    brief = service.generate(job_title="Platform Engineer")

    assert brief.company == "the hiring team"
    assert "Platform Engineer" in brief.likely_questions[0]
    assert brief.focus_gaps
    assert brief.requires_human_review is True


def test_generate_brief_never_performs_http() -> None:
    """Interview prep must not open network connections."""

    service = InterviewPrepBriefService()
    with (
        patch.object(httpx, "Client", side_effect=AssertionError("no httpx.Client")),
        patch.object(httpx, "AsyncClient", side_effect=AssertionError("no AsyncClient")),
        patch("httpx.post", MagicMock(side_effect=AssertionError("no httpx.post"))),
        patch("httpx.get", MagicMock(side_effect=AssertionError("no httpx.get"))),
    ):
        brief = service.generate(
            job_title="Data Engineer",
            company="Example",
            job_text="Spark and SQL pipelines.",
        )

    assert brief.requires_human_review is True
    assert any("Data Engineer" in q for q in brief.likely_questions)


def test_generate_brief_is_deterministic() -> None:
    """Same inputs produce identical briefs."""

    service = InterviewPrepBriefService()
    kwargs = {
        "job_title": "SRE",
        "company": "OpsCo",
        "job_text": "Kubernetes remote leadership role.",
        "candidate_skills": ["kubernetes"],
    }
    assert service.generate(**kwargs) == service.generate(**kwargs)


def test_leadership_title_adds_coaching_question() -> None:
    """Lead/manager titles add a coaching-oriented question."""

    brief = InterviewPrepBriefService().generate(job_title="Engineering Manager")
    assert any("coach" in q.lower() for q in brief.likely_questions)

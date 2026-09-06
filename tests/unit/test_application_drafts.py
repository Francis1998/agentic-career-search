"""Unit tests for ApplicationDraftService (HITL, no network apply)."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import httpx

from autoapply_agent.services.application_drafts import ApplicationDraftService

if TYPE_CHECKING:
    from _pytest.capture import CaptureFixture
    from _pytest.fixtures import FixtureRequest
    from _pytest.logging import LogCaptureFixture
    from _pytest.monkeypatch import MonkeyPatch
    from pytest_mock.plugin import MockerFixture


def test_generate_draft_includes_bullets_and_cover_note() -> None:
    """Drafts include resume bullets and a cover note for the target role."""

    service = ApplicationDraftService()
    draft = service.generate(
        job_title="Senior Backend Engineer",
        company="Acme Labs",
        query="python fastapi",
    )

    assert draft.job_title == "Senior Backend Engineer"
    assert draft.company == "Acme Labs"
    assert len(draft.resume_bullets) >= 3
    assert "Senior Backend Engineer" in draft.cover_note
    assert "Acme Labs" in draft.cover_note
    assert "python fastapi" in draft.cover_note
    assert draft.requires_human_review is True
    assert draft.auto_submit is False


def test_generate_draft_handles_missing_company_and_query() -> None:
    """Missing company/query still yields a usable HITL draft."""

    service = ApplicationDraftService()
    draft = service.generate(job_title="Platform Engineer")

    assert draft.company == "the hiring team"
    assert draft.query is None
    assert "Platform Engineer" in draft.cover_note
    assert "Draft only" in draft.cover_note


def test_generate_draft_never_performs_http_apply() -> None:
    """Draft generation must not open network connections or submit forms."""

    service = ApplicationDraftService()
    with (
        patch.object(httpx, "Client", side_effect=AssertionError("no httpx.Client")),
        patch.object(httpx, "AsyncClient", side_effect=AssertionError("no AsyncClient")),
        patch("httpx.post", MagicMock(side_effect=AssertionError("no httpx.post"))),
        patch("httpx.get", MagicMock(side_effect=AssertionError("no httpx.get"))),
    ):
        draft = service.generate(
            job_title="Data Engineer",
            company="Example",
            query="spark",
        )

    assert draft.auto_submit is False
    assert draft.requires_human_review is True
    assert any("Data Engineer" in bullet for bullet in draft.resume_bullets)


def test_generate_draft_is_deterministic() -> None:
    """Same inputs produce identical drafts."""

    service = ApplicationDraftService()
    first = service.generate(
        job_title="SRE",
        company="OpsCo",
        query="kubernetes",
    )
    second = service.generate(
        job_title="SRE",
        company="OpsCo",
        query="kubernetes",
    )
    assert first == second

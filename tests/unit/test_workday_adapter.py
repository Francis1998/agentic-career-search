"""Unit tests for the Workday public CXS JSON adapter."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from autoapply_agent.adapters.base import SourceAdapterError
from autoapply_agent.adapters.workday import WorkdayAdapter

if TYPE_CHECKING:
    from _pytest.capture import CaptureFixture
    from _pytest.fixtures import FixtureRequest
    from _pytest.logging import LogCaptureFixture
    from _pytest.monkeypatch import MonkeyPatch
    from pytest_mock.plugin import MockerFixture


WORKDAY_SAMPLE_PAYLOAD = """
{
  "total": 2,
  "jobPostings": [
    {
      "title": "Senior CPU Performance Architect",
      "externalPath": "/job/US-CA-Santa-Clara/Senior-CPU-Performance-Architect_JR2018189",
      "locationsText": "Santa Clara, CA"
    },
    {
      "title": "Staff Software Engineer",
      "externalPath": "/job/US-Remote/Staff-Software-Engineer_R-9001",
      "locationsText": "Remote - US"
    }
  ]
}
"""


def test_workday_parses_postings() -> None:
    """The adapter maps ``jobPostings`` records onto normalized candidates."""

    adapter = WorkdayAdapter(user_agent="test-agent")
    board = adapter._parse_board(
        "https://nvidia.wd5.myworkdayjobs.com/en-US/NVIDIAExternalCareerSite"
    )
    jobs = adapter._parse_payload(board, WORKDAY_SAMPLE_PAYLOAD, max_jobs=10)

    by_title = {job.title: job for job in jobs}
    assert set(by_title) == {"Senior CPU Performance Architect", "Staff Software Engineer"}

    cpu = by_title["Senior CPU Performance Architect"]
    assert cpu.external_id == "JR2018189"
    assert cpu.location == "Santa Clara, CA"
    assert cpu.url == (
        "https://nvidia.wd5.myworkdayjobs.com/en-US/NVIDIAExternalCareerSite"
        "/job/US-CA-Santa-Clara/Senior-CPU-Performance-Architect_JR2018189"
    )
    assert cpu.company == "nvidia.wd5.myworkdayjobs.com"
    assert cpu.raw == {"source": "workday"}

    assert by_title["Staff Software Engineer"].external_id == "R-9001"


def test_workday_parse_board_defaults_locale_when_absent() -> None:
    """A careers URL without a locale segment defaults locale to ``en-US``."""

    adapter = WorkdayAdapter(user_agent="test-agent")
    board = adapter._parse_board("https://acme.wd1.myworkdayjobs.com/Acme_External_Careers")

    assert board["tenant"] == "acme"
    assert board["site"] == "Acme_External_Careers"
    assert board["locale"] == "en-US"
    assert board["cxs_url"] == (
        "https://acme.wd1.myworkdayjobs.com/wday/cxs/acme/Acme_External_Careers/jobs"
    )


def test_workday_skips_records_missing_path_or_title() -> None:
    """Records without a usable title or externalPath are ignored."""

    adapter = WorkdayAdapter(user_agent="test-agent")
    board = adapter._parse_board("https://acme.wd1.myworkdayjobs.com/en-US/AcmeCareers")
    payload = """
    {"jobPostings": [
      {"title": "Ghost", "externalPath": " "},
      {"externalPath": "/job/X_JR1"},
      {"title": "Real Role", "externalPath": "/job/X_JR2"}
    ]}
    """
    jobs = adapter._parse_payload(board, payload, max_jobs=10)

    assert [job.title for job in jobs] == ["Real Role"]
    assert jobs[0].external_id == "JR2"


def test_workday_rejects_unrecognised_host() -> None:
    """Non-Workday hosts must raise ``SourceAdapterError``."""

    adapter = WorkdayAdapter(user_agent="test-agent")
    with pytest.raises(SourceAdapterError, match="unrecognised Workday"):
        adapter._parse_board("https://boards.greenhouse.io/acme")


def test_workday_rejects_invalid_json() -> None:
    """Malformed CXS payloads raise ``SourceAdapterError``."""

    adapter = WorkdayAdapter(user_agent="test-agent")
    board = adapter._parse_board("https://acme.wd1.myworkdayjobs.com/en-US/AcmeCareers")
    with pytest.raises(SourceAdapterError, match="invalid Workday JSON"):
        adapter._parse_payload(board, "{not-json", max_jobs=10)


def test_workday_honors_zero_max_jobs() -> None:
    """A non-positive max_jobs must yield no candidates."""

    adapter = WorkdayAdapter(user_agent="test-agent")
    board = adapter._parse_board("https://acme.wd1.myworkdayjobs.com/en-US/AcmeCareers")
    jobs = adapter._parse_payload(board, WORKDAY_SAMPLE_PAYLOAD, max_jobs=0)

    assert jobs == []


def test_workday_referer_uses_board_locale_not_hardcoded_en_us() -> None:
    """CXS Referer must mirror the board locale (not a hardcoded ``en-US``)."""

    import asyncio
    from typing import Any

    from autoapply_agent.adapters import workday as workday_module

    captured: dict[str, Any] = {}

    class _FakeResponse:
        text = WORKDAY_SAMPLE_PAYLOAD

        def raise_for_status(self) -> None:
            return None

    class _FakeAsyncClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            captured["client_headers"] = kwargs.get("headers")

        async def __aenter__(self) -> _FakeAsyncClient:
            return self

        async def __aexit__(self, *exc_info: object) -> bool:
            return False

        async def post(self, *args: Any, **kwargs: Any) -> _FakeResponse:
            return _FakeResponse()

    adapter = WorkdayAdapter(user_agent="test-agent")
    board = adapter._parse_board(
        "https://acme.wd1.myworkdayjobs.com/fr-FR/AcmeCareers"
    )
    assert board["locale"] == "fr-FR"

    original_client = workday_module.httpx.AsyncClient
    workday_module.httpx.AsyncClient = _FakeAsyncClient  # type: ignore[misc,assignment]
    try:
        asyncio.run(
            adapter._request_cxs_page(
                board["cxs_url"],
                board["origin"],
                board["site"],
                board["locale"],
                timeout_seconds=5.0,
                limit=20,
                offset=0,
            )
        )
    finally:
        workday_module.httpx.AsyncClient = original_client  # type: ignore[misc]

    assert captured["client_headers"]["Referer"] == (
        "https://acme.wd1.myworkdayjobs.com/fr-FR/AcmeCareers"
    )
    assert "en-US" not in captured["client_headers"]["Referer"]

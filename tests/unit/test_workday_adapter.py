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

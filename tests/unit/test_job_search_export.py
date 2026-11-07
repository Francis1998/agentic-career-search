"""Unit tests for the job search helpers and the CSV / JSON Lines / Atom renderers."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import UTC, datetime, timedelta, timezone

import pytest

from autoapply_agent.db.models import Job
from autoapply_agent.schemas.jobs import JobRead
from autoapply_agent.services.job_export import (
    CSV_COLUMNS,
    entry_id,
    job_csv_row,
    job_jsonl_line,
    neutralize_csv_cell,
    render_atom_feed,
    rfc3339,
    safe_http_url,
)
from autoapply_agent.services.job_search import as_utc, is_remote_location, posting_key

ATOM = "{http://www.w3.org/2005/Atom}"


def _job(**overrides: object) -> Job:
    """Build a transient job with sensible defaults."""

    fields: dict[str, object] = {
        "id": 7,
        "run_id": "run-1",
        "source_config_id": 3,
        "external_id": "ext-7",
        "title": "Senior Python Engineer",
        "location": "Remote - US",
        "company": "Acme",
        "url": "https://jobs.example.com/7",
        "score": 0.875,
        "plan_steps": ["Review fit"],
        "raw": {"source": "greenhouse", "agent_decision": {"priority_tier": "high"}},
        "created_at": datetime(2026, 11, 6, 18, 30, 5, 123456),
    }
    fields.update(overrides)
    return Job(**fields)


@pytest.mark.parametrize(
    ("location", "expected"),
    [
        ("Remote - US", True),
        ("Anywhere", True),
        ("Work From Home (UK)", True),
        ("WFH", True),
        ("Distributed team", True),
        ("Telecommute", True),
        ("Berlin, Germany", False),
        ("", False),
        (None, False),
    ],
)
def test_is_remote_location(location: str | None, expected: bool) -> None:
    """The remote rule is a case-insensitive keyword match on the location."""

    assert is_remote_location(location) is expected


def test_posting_key_normalizes_company_suffixes_but_keeps_locations_apart() -> None:
    """Mirrors collapse across punctuation/legal suffixes; other cities stay distinct."""

    assert posting_key("Senior SWE", "Acme, Inc.", "Remote - US") == posting_key(
        "senior swe", "ACME", "remote (us)"
    )
    assert posting_key("Senior SWE", "Acme", "Berlin") != posting_key("Senior SWE", "Acme", "Paris")


def test_as_utc_and_rfc3339_treat_naive_values_as_utc() -> None:
    """Naive datetimes (SQLite) are UTC; offsets are converted."""

    naive = datetime(2026, 11, 6, 18, 30, 5, 999)
    pacific = datetime(2026, 11, 6, 10, 30, 5, tzinfo=timezone(timedelta(hours=-8)))

    assert as_utc(naive) == datetime(2026, 11, 6, 18, 30, 5, 999, tzinfo=UTC)
    assert rfc3339(naive) == "2026-11-06T18:30:05Z"
    assert rfc3339(pacific) == "2026-11-06T18:30:05Z"


@pytest.mark.parametrize("trigger", ["=", "+", "-", "@", "\t", "\r"])
def test_neutralize_csv_cell_prefixes_every_owasp_trigger(trigger: str) -> None:
    """Cells starting with a formula trigger are prefixed with a single quote."""

    assert neutralize_csv_cell(f"{trigger}1+1") == f"'{trigger}1+1"


@pytest.mark.parametrize("value", ["Senior Engineer", "", "a=b", " =1+1", "'quoted"])
def test_neutralize_csv_cell_keeps_safe_values(value: str) -> None:
    """Only a leading trigger character changes the cell."""

    assert neutralize_csv_cell(value) == value


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://jobs.example.com/1", "https://jobs.example.com/1"),
        (" HTTP://jobs.example.com/1 ", "HTTP://jobs.example.com/1"),
        ("javascript:alert(1)", None),
        ("data:text/html,<b>x</b>", None),
        ("ftp://jobs.example.com/1", None),
        ("/jobs/1", None),
        ("https://", None),
        ("http://[::1", None),
        ("", None),
        (None, None),
    ],
)
def test_safe_http_url(url: str | None, expected: str | None) -> None:
    """Only absolute http(s) URLs survive."""

    assert safe_http_url(url) == expected


def test_job_csv_row_matches_columns_and_handles_missing_fields() -> None:
    """Rows align with the header; missing optional fields become empty cells."""

    full = dict(zip(CSV_COLUMNS, job_csv_row(_job()), strict=True))
    sparse = dict(
        zip(
            CSV_COLUMNS,
            job_csv_row(
                _job(company=None, location=None, source_config_id=None, external_id=None, raw=None)
            ),
            strict=True,
        )
    )

    assert full == {
        "id": "7",
        "title": "Senior Python Engineer",
        "company": "Acme",
        "location": "Remote - US",
        "remote": "true",
        "score": "0.875",
        "priority_tier": "high",
        "source": "greenhouse",
        "url": "https://jobs.example.com/7",
        "source_config_id": "3",
        "run_id": "run-1",
        "external_id": "ext-7",
        "created_at": "2026-11-06T18:30:05Z",
    }
    assert sparse["company"] == sparse["location"] == sparse["priority_tier"] == ""
    assert sparse["remote"] == "false"
    assert sparse["source_config_id"] == sparse["external_id"] == ""


def test_job_jsonl_line_round_trips() -> None:
    """A JSON Lines record parses back into the same API model."""

    job = _job()
    line = job_jsonl_line(job)

    assert line.endswith("\n")
    assert line.count("\n") == 1
    assert JobRead.model_validate_json(line) == JobRead.model_validate(job)


def test_entry_id_is_a_stable_uuid_urn_per_posting_url() -> None:
    """Re-captures of one URL share an id; different URLs do not."""

    assert entry_id(_job(id=1)) == entry_id(_job(id=99, title="Renamed"))
    assert entry_id(_job(url="https://jobs.example.com/8")) != entry_id(_job())
    assert entry_id(_job()).startswith("urn:uuid:")


def test_render_atom_feed_with_and_without_entries() -> None:
    """Both an empty and a populated feed parse and carry the required elements."""

    generated_at = datetime(2026, 11, 7, 1, 2, 3, tzinfo=UTC)
    empty = ET.fromstring(
        render_atom_feed(
            [],
            feed_id="urn:uuid:feed",
            title="Jobs",
            self_url="http://localhost:8000/jobs/feed.atom",
            fallback_link=lambda job: f"http://localhost:8000/jobs/{job.id}",
            generated_at=generated_at,
        )
    )
    document = render_atom_feed(
        [_job(url="javascript:alert(1)", title="A & B <c>")],
        feed_id="urn:uuid:feed",
        title="Jobs",
        self_url="http://localhost:8000/jobs/feed.atom?q=a&remote=true",
        fallback_link=lambda job: f"http://localhost:8000/jobs/{job.id}",
        generated_at=generated_at,
    )
    populated = ET.fromstring(document)

    assert empty.findtext(f"{ATOM}updated") == "2026-11-07T01:02:03Z"
    assert empty.findall(f"{ATOM}entry") == []
    assert document.startswith(b"<?xml version='1.0' encoding='utf-8'?>")
    assert b"q=a&amp;remote=true" in document
    entry = populated.find(f"{ATOM}entry")
    assert entry is not None
    assert entry.findtext(f"{ATOM}title") == "A & B <c> at Acme"
    link = entry.find(f"{ATOM}link")
    assert link is not None
    assert link.get("href") == "http://localhost:8000/jobs/7"
    assert populated.findtext(f"{ATOM}updated") == "2026-11-06T18:30:05Z"
    assert entry.findtext(f"{ATOM}summary") == (
        "Company: Acme | Location: Remote - US | Remote: yes | Score: 0.88 | Priority: high"
    )

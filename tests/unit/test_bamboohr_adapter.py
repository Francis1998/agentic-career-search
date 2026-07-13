"""Unit tests for the BambooHR hosted careers JSON adapter."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from autoapply_agent.adapters.bamboohr import BambooHrAdapter
from autoapply_agent.adapters.base import SourceAdapterError

if TYPE_CHECKING:
    from _pytest.capture import CaptureFixture
    from _pytest.fixtures import FixtureRequest
    from _pytest.logging import LogCaptureFixture
    from _pytest.monkeypatch import MonkeyPatch
    from pytest_mock.plugin import MockerFixture


BAMBOOHR_SAMPLE_PAYLOAD = """
{
  "result": [
    {
      "id": 4821,
      "jobOpeningName": "Senior Platform Engineer",
      "location": {"city": "Lindon", "state": "Utah", "country": "United States"},
      "isRemote": false
    },
    {
      "id": "4822",
      "jobOpeningName": "Product Designer",
      "location": "Remote - US",
      "isRemote": true
    },
    {
      "id": 4823,
      "jobOpeningName": "Staff SRE",
      "isRemote": true
    }
  ]
}
"""


def test_bamboohr_parses_openings() -> None:
    """The adapter maps ``result`` records onto normalized candidates."""

    adapter = BambooHrAdapter(user_agent="test-agent")
    jobs = adapter._parse_payload(
        "https://acme.bamboohr.com/careers/list",
        BAMBOOHR_SAMPLE_PAYLOAD,
        max_jobs=10,
    )

    by_title = {job.title: job for job in jobs}
    assert set(by_title) == {"Senior Platform Engineer", "Product Designer", "Staff SRE"}

    platform = by_title["Senior Platform Engineer"]
    assert platform.external_id == "4821"
    assert platform.location == "Lindon, Utah, United States"
    assert platform.url == "https://acme.bamboohr.com/careers/4821"
    assert platform.company == "acme.bamboohr.com"

    assert by_title["Product Designer"].location == "Remote - US"
    # A remote opening with no location block falls back to "Remote".
    assert by_title["Staff SRE"].location == "Remote"


def test_bamboohr_skips_blank_id_rows() -> None:
    """Rows with a blank/whitespace id must be skipped, not collapsed.

    BambooHR occasionally emits rows whose ``id`` is empty or whitespace. A
    blank id would build the bare ``/careers/`` URL for every such row, so URL
    deduplication would silently discard all but the first distinct posting.
    Skipping those rows keeps the remaining postings intact and phantom-free.
    """

    adapter = BambooHrAdapter(user_agent="test-agent")
    payload = """
    {"result": [
      {"id": " ", "jobOpeningName": "Ghost One"},
      {"id": "", "jobOpeningName": "Ghost Two"},
      {"id": 501, "jobOpeningName": "Real Role"}
    ]}
    """
    jobs = adapter._parse_payload("https://acme.bamboohr.com/careers/list", payload, max_jobs=10)

    assert [job.title for job in jobs] == ["Real Role"]
    assert jobs[0].url == "https://acme.bamboohr.com/careers/501"


def test_bamboohr_skips_records_missing_title() -> None:
    """Records without a usable ``jobOpeningName`` are ignored."""

    adapter = BambooHrAdapter(user_agent="test-agent")
    payload = '{"result": [{"id": 7}, {"id": 8, "jobOpeningName": "   "}]}'
    jobs = adapter._parse_payload("https://acme.bamboohr.com/careers/list", payload, max_jobs=10)

    assert jobs == []


def test_bamboohr_honors_zero_max_jobs() -> None:
    """A non-positive max_jobs must yield no candidates."""

    adapter = BambooHrAdapter(user_agent="test-agent")
    jobs = adapter._parse_payload(
        "https://acme.bamboohr.com/careers/list", BAMBOOHR_SAMPLE_PAYLOAD, max_jobs=0
    )

    assert jobs == []


def test_bamboohr_invalid_json_raises() -> None:
    """A non-JSON payload surfaces as a SourceAdapterError."""

    adapter = BambooHrAdapter(user_agent="test-agent")
    with pytest.raises(SourceAdapterError):
        adapter._parse_payload(
            "https://acme.bamboohr.com/careers/list", "<html>not json</html>", max_jobs=10
        )


def test_bamboohr_list_url_is_derived_from_any_careers_url() -> None:
    """The list endpoint is derived from the tenant origin, not the given path."""

    adapter = BambooHrAdapter(user_agent="test-agent")
    assert (
        adapter._list_url("https://acme.bamboohr.com/careers")
        == "https://acme.bamboohr.com/careers/list"
    )
    assert (
        adapter._list_url("https://acme.bamboohr.com/careers/4821")
        == "https://acme.bamboohr.com/careers/list"
    )

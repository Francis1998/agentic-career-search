"""Unit tests for source adapter HTML parsing."""

from __future__ import annotations

from typing import TYPE_CHECKING

from autoapply_agent.adapters.greenhouse import GreenhouseAdapter
from autoapply_agent.adapters.lever import LeverAdapter

if TYPE_CHECKING:
    from _pytest.capture import CaptureFixture
    from _pytest.fixtures import FixtureRequest
    from _pytest.logging import LogCaptureFixture
    from _pytest.monkeypatch import MonkeyPatch
    from pytest_mock.plugin import MockerFixture


GREENHOUSE_SAMPLE_HTML = """
<div class=\"opening\">
  <a href=\"/example/jobs/12345?gh_jid=12345\">Backend Engineer</a>
  <span class=\"location\">Remote</span>
</div>
"""


LEVER_SAMPLE_HTML = """
<div class=\"posting\">
  <a class=\"posting-title\" href=\"/company/jobs/abc-987\">Data Engineer</a>
  <span class=\"sort-by-location\">Austin, TX</span>
</div>
"""


def test_greenhouse_parser_extracts_jobs() -> None:
    """Greenhouse parser should extract expected candidate fields."""

    adapter = GreenhouseAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://boards.greenhouse.io/embed/job_board?for=example",
        GREENHOUSE_SAMPLE_HTML,
        max_jobs=10,
    )

    assert len(jobs) == 1
    assert jobs[0].title == "Backend Engineer"
    assert jobs[0].external_id == "12345"
    assert jobs[0].location == "Remote"


def test_lever_parser_extracts_jobs() -> None:
    """Lever parser should extract expected candidate fields."""

    adapter = LeverAdapter(user_agent="test-agent")
    jobs = adapter._parse_html("https://jobs.lever.co/company", LEVER_SAMPLE_HTML, max_jobs=10)

    assert len(jobs) == 1
    assert jobs[0].title == "Data Engineer"
    assert jobs[0].external_id == "abc-987"
    assert jobs[0].location == "Austin, TX"


def test_greenhouse_parser_honors_zero_max_jobs() -> None:
    """A non-positive max_jobs must yield no candidates, not one."""

    adapter = GreenhouseAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://boards.greenhouse.io/embed/job_board?for=example",
        GREENHOUSE_SAMPLE_HTML,
        max_jobs=0,
    )

    assert jobs == []


def test_lever_parser_honors_zero_max_jobs() -> None:
    """A non-positive max_jobs must yield no candidates, not one."""

    adapter = LeverAdapter(user_agent="test-agent")
    jobs = adapter._parse_html("https://jobs.lever.co/company", LEVER_SAMPLE_HTML, max_jobs=0)

    assert jobs == []

"""Unit tests for the Phenom careers portal adapter."""

from __future__ import annotations

from autoapply_agent.adapters.phenom import PhenomAdapter

PHENOM_SAMPLE_HTML = """
<html>
  <body>
    <ul class="jobs-list">
      <li class="job">
        <a href="/us/en/job/1234567/platform-engineer">
          Platform Engineer
        </a>
        <span class="job-location">Phoenix, AZ</span>
      </li>
      <li class="job">
        <a href="/en-US/job/JR-7788" title="Site Reliability Engineer"></a>
        <span class="job-location">Remote</span>
      </li>
      <li class="job">
        <a href="/jobs/9001">Data Engineer</a>
        <span class="job-location">Austin, TX</span>
      </li>
    </ul>
    <a href="/us/en/job/1234567/platform-engineer/apply">Apply</a>
    <a href="/us/en/jobs/search">Search</a>
    <a href="/about">About</a>
  </body>
</html>
"""


def test_phenom_parser_extracts_jobs() -> None:
    """Phenom parser should extract posting fields and skip apply/search links."""

    adapter = PhenomAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://careers.acme.phenompeople.com/us/en/search-results",
        PHENOM_SAMPLE_HTML,
        max_jobs=10,
    )

    by_title = {job.title: job for job in jobs}
    assert set(by_title) == {
        "Platform Engineer",
        "Site Reliability Engineer",
        "Data Engineer",
    }
    assert by_title["Platform Engineer"].external_id == "1234567"
    assert by_title["Platform Engineer"].location == "Phoenix, AZ"
    assert by_title["Platform Engineer"].url.endswith("/us/en/job/1234567/platform-engineer")
    assert by_title["Site Reliability Engineer"].external_id == "JR-7788"
    assert by_title["Data Engineer"].external_id == "9001"


def test_phenom_parser_ignores_non_posting_links() -> None:
    """Apply steps, search pages, and nav links are not postings."""

    adapter = PhenomAdapter(user_agent="test-agent")
    nav_only_html = """
    <a href="/us/en/job/1234567/platform-engineer/apply">Apply</a>
    <a href="/us/en/jobs/search">Search</a>
    <a href="/about">About</a>
    """
    jobs = adapter._parse_html(
        "https://careers.acme.phenompeople.com/us/en/search-results",
        nav_only_html,
        max_jobs=10,
    )

    assert jobs == []


def test_phenom_parser_honors_zero_max_jobs() -> None:
    """A non-positive max_jobs must yield no candidates."""

    adapter = PhenomAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://careers.acme.phenompeople.com/us/en/search-results",
        PHENOM_SAMPLE_HTML,
        max_jobs=0,
    )

    assert jobs == []


def test_phenom_location_is_scoped_to_its_posting() -> None:
    """A posting without its own location must not inherit a sibling's location."""

    adapter = PhenomAdapter(user_agent="test-agent")
    html = """
    <div class="job">
      <a href="/job/1001"><h4>First Role</h4></a>
    </div>
    <div class="job">
      <a href="/job/1002"><h4>Second Role</h4></a>
      <span class="job-location">Austin</span>
    </div>
    """
    jobs = adapter._parse_html(
        "https://careers.acme.phenompeople.com/us/en/search-results", html, max_jobs=10
    )

    by_title = {job.title: job for job in jobs}
    assert by_title["First Role"].location is None
    assert by_title["Second Role"].location == "Austin"

"""Unit tests for the Oracle Taleo careers portal adapter."""

from __future__ import annotations

from autoapply_agent.adapters.oracle_taleo import OracleTaleoAdapter

TALEO_SAMPLE_HTML = """
<html>
  <body>
    <table class="jobboard">
      <tr class="job">
        <td>
          <a href="/careersection/ex/jobdetail.ftl?job=123456&lang=en">
            Platform Engineer
          </a>
          <span class="job-location">Austin, TX</span>
        </td>
      </tr>
      <tr class="job">
        <td>
          <a href="/jobs/JR-7788" title="Site Reliability Engineer"></a>
          <span class="job-location">Remote</span>
        </td>
      </tr>
    </table>
    <a href="/careersection/ex/jobdetail.ftl?job=123456&mode=apply">Apply</a>
    <a href="/careersection/ex/jobsearch.ftl">Search</a>
    <a href="/about">About</a>
  </body>
</html>
"""


def test_oracle_taleo_parser_extracts_jobs() -> None:
    """Taleo parser should extract posting fields and skip apply/search links."""

    adapter = OracleTaleoAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://acme.taleo.net/careersection/ex/jobsearch.ftl",
        TALEO_SAMPLE_HTML,
        max_jobs=10,
    )

    by_title = {job.title: job for job in jobs}
    assert set(by_title) == {"Platform Engineer", "Site Reliability Engineer"}
    assert by_title["Platform Engineer"].external_id == "123456"
    assert by_title["Platform Engineer"].location == "Austin, TX"
    assert by_title["Platform Engineer"].url.endswith("job=123456&lang=en")
    assert by_title["Site Reliability Engineer"].external_id == "JR-7788"
    assert by_title["Site Reliability Engineer"].url.endswith("/jobs/JR-7788")


def test_oracle_taleo_parser_ignores_non_posting_links() -> None:
    """Apply steps, search pages, and nav links are not postings."""

    adapter = OracleTaleoAdapter(user_agent="test-agent")
    nav_only_html = """
    <a href="/careersection/ex/jobdetail.ftl?job=123456&mode=apply">Apply</a>
    <a href="/careersection/ex/jobsearch.ftl">Search</a>
    <a href="/about">About</a>
    """
    jobs = adapter._parse_html(
        "https://acme.taleo.net/careersection/ex/jobsearch.ftl",
        nav_only_html,
        max_jobs=10,
    )

    assert jobs == []


def test_oracle_taleo_parser_honors_zero_max_jobs() -> None:
    """A non-positive max_jobs must yield no candidates."""

    adapter = OracleTaleoAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://acme.taleo.net/careersection/ex/jobsearch.ftl",
        TALEO_SAMPLE_HTML,
        max_jobs=0,
    )

    assert jobs == []


def test_oracle_taleo_location_is_scoped_to_its_posting() -> None:
    """A posting without its own location must not inherit a sibling's location."""

    adapter = OracleTaleoAdapter(user_agent="test-agent")
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
        "https://acme.taleo.net/careersection/ex/jobsearch.ftl", html, max_jobs=10
    )

    by_title = {job.title: job for job in jobs}
    assert by_title["First Role"].location is None
    assert by_title["Second Role"].location == "Austin"

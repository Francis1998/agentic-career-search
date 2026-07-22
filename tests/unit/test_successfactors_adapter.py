"""Unit tests for the SAP SuccessFactors careers portal adapter."""

from __future__ import annotations

from autoapply_agent.adapters.successfactors import SuccessFactorsAdapter

SUCCESSFACTORS_SAMPLE_HTML = """
<html>
  <body>
    <table class="jobboard">
      <tr class="job">
        <td>
          <a href="/sfcareer/jobreqcareer?jobId=123456&company=ACME">
            Platform Engineer
          </a>
          <span class="job-location">Walldorf, DE</span>
        </td>
      </tr>
      <tr class="job">
        <td>
          <a href="/career?career_job_req_id=JR-7788&company=ACME"
             title="Site Reliability Engineer"></a>
          <span class="job-location">Remote</span>
        </td>
      </tr>
      <tr class="job">
        <td>
          <a href="/jobs/9001">Data Engineer</a>
          <span class="job-location">New York, NY</span>
        </td>
      </tr>
    </table>
    <a href="/sfcareer/jobreqcareer?jobId=123456&mode=apply">Apply</a>
    <a href="/career?career_ns=job_listing">Search</a>
    <a href="/about">About</a>
  </body>
</html>
"""


def test_successfactors_parser_extracts_jobs() -> None:
    """SuccessFactors parser should extract posting fields and skip apply/search."""

    adapter = SuccessFactorsAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://career5.successfactors.eu/career?company=ACME",
        SUCCESSFACTORS_SAMPLE_HTML,
        max_jobs=10,
    )

    by_title = {job.title: job for job in jobs}
    assert set(by_title) == {
        "Platform Engineer",
        "Site Reliability Engineer",
        "Data Engineer",
    }
    assert by_title["Platform Engineer"].external_id == "123456"
    assert by_title["Platform Engineer"].location == "Walldorf, DE"
    assert "jobId=123456" in by_title["Platform Engineer"].url
    assert by_title["Site Reliability Engineer"].external_id == "JR-7788"
    assert by_title["Data Engineer"].external_id == "9001"
    assert by_title["Data Engineer"].url.endswith("/jobs/9001")


def test_successfactors_parser_ignores_non_posting_links() -> None:
    """Apply steps, search pages, and nav links are not postings."""

    adapter = SuccessFactorsAdapter(user_agent="test-agent")
    nav_only_html = """
    <a href="/sfcareer/jobreqcareer?jobId=123456&mode=apply">Apply</a>
    <a href="/career?career_ns=job_listing">Search</a>
    <a href="/about">About</a>
    """
    jobs = adapter._parse_html(
        "https://career5.successfactors.eu/career?company=ACME",
        nav_only_html,
        max_jobs=10,
    )

    assert jobs == []


def test_successfactors_parser_honors_zero_max_jobs() -> None:
    """A non-positive max_jobs must yield no candidates."""

    adapter = SuccessFactorsAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://career5.successfactors.eu/career?company=ACME",
        SUCCESSFACTORS_SAMPLE_HTML,
        max_jobs=0,
    )

    assert jobs == []


def test_successfactors_location_is_scoped_to_its_posting() -> None:
    """A posting without its own location must not inherit a sibling's location."""

    adapter = SuccessFactorsAdapter(user_agent="test-agent")
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
        "https://career5.successfactors.eu/career?company=ACME", html, max_jobs=10
    )

    by_title = {job.title: job for job in jobs}
    assert by_title["First Role"].location is None
    assert by_title["Second Role"].location == "Austin"

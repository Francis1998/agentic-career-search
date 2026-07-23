"""Unit tests for the Zoho Recruit careers portal adapter."""

from __future__ import annotations

from autoapply_agent.adapters.zoho_recruit import ZohoRecruitAdapter

ZOHO_RECRUIT_SAMPLE_HTML = """
<html>
  <body>
    <table class="jobboard">
      <tr class="job">
        <td>
          <a href="/jobs/Careers?jobId=ZR-1234">
            Platform Engineer
          </a>
          <span class="job-location">Austin, TX</span>
        </td>
      </tr>
      <tr class="job">
        <td>
          <a href="/jobs/Careers?jid=ZR_7788" title="Site Reliability Engineer"></a>
          <span class="job-location">Remote</span>
        </td>
      </tr>
      <tr class="job">
        <td>
          <a href="/jobs/Careers?job_id=9001">Data Engineer</a>
          <span class="job-location">New York, NY</span>
        </td>
      </tr>
      <tr class="job">
        <td>
          <a href="/jobs/ABCD99">Analytics Engineer</a>
          <span class="job-location">Toronto, CA</span>
        </td>
      </tr>
      <tr class="job">
        <td>
          <a href="/job/ABC-42">Product Engineer</a>
          <span class="job-location">London, UK</span>
        </td>
      </tr>
      <tr class="job">
        <td>
          <a href="/careers/ZR-5555">Security Engineer</a>
          <span class="job-location">Berlin, DE</span>
        </td>
      </tr>
      <tr class="job">
        <td>
          <a href="/Jobs/Careers/ZR-9999">Solutions Architect</a>
          <span class="job-location">Singapore</span>
        </td>
      </tr>
    </table>
    <a href="/jobs/Careers?jobId=ZR-1234&source=apply">Apply</a>
    <a href="/jobs/Careers?jobId=ZR-1234&mode=apply">Apply now</a>
    <a href="/jobs/Careers">Search</a>
    <a href="/about">About</a>
  </body>
</html>
"""


def test_zoho_recruit_parser_extracts_jobs() -> None:
    """Zoho Recruit parser should extract posting fields and skip apply/search."""

    adapter = ZohoRecruitAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://acme.zohorecruit.com/jobs/Careers",
        ZOHO_RECRUIT_SAMPLE_HTML,
        max_jobs=10,
    )

    by_title = {job.title: job for job in jobs}
    assert set(by_title) == {
        "Platform Engineer",
        "Site Reliability Engineer",
        "Data Engineer",
        "Analytics Engineer",
        "Product Engineer",
        "Security Engineer",
        "Solutions Architect",
    }
    assert by_title["Platform Engineer"].external_id == "ZR-1234"
    assert by_title["Platform Engineer"].location == "Austin, TX"
    assert "jobId=ZR-1234" in by_title["Platform Engineer"].url
    assert by_title["Site Reliability Engineer"].external_id == "ZR_7788"
    assert by_title["Data Engineer"].external_id == "9001"
    assert by_title["Analytics Engineer"].external_id == "ABCD99"
    assert by_title["Analytics Engineer"].url.endswith("/jobs/ABCD99")
    assert by_title["Product Engineer"].external_id == "ABC-42"
    assert by_title["Security Engineer"].external_id == "ZR-5555"
    assert by_title["Solutions Architect"].external_id == "ZR-9999"


def test_zoho_recruit_anchor_title_falls_back_to_title_attribute() -> None:
    """Empty-text Zoho Recruit anchors with a title= attribute must be kept."""

    adapter = ZohoRecruitAdapter(user_agent="test-agent")
    html = """
    <div class="job">
      <a href="/jobs/Careers?jobId=ZR-7777" title="Staff Platform Engineer"></a>
      <span class="job-location">Remote</span>
    </div>
    """
    jobs = adapter._parse_html("https://acme.zohorecruit.com/jobs/Careers", html, max_jobs=10)

    assert len(jobs) == 1
    assert jobs[0].title == "Staff Platform Engineer"
    assert jobs[0].external_id == "ZR-7777"
    assert jobs[0].location == "Remote"


def test_zoho_recruit_parser_ignores_apply_and_non_posting_links() -> None:
    """Apply steps, search pages, and nav links are not postings."""

    adapter = ZohoRecruitAdapter(user_agent="test-agent")
    nav_only_html = """
    <a href="/jobs/Careers?jobId=ZR-1234&source=apply">Apply source</a>
    <a href="/jobs/Careers?jobId=ZR-1234&mode=apply">Apply mode</a>
    <a href="/jobs/ZR-1234/apply">Apply terminal</a>
    <a href="/jobs/ZR-1234/login">Login terminal</a>
    <a href="/jobs/Careers">Search</a>
    <a href="/about">About</a>
    """
    jobs = adapter._parse_html(
        "https://acme.zohorecruit.com/jobs/Careers",
        nav_only_html,
        max_jobs=10,
    )

    assert jobs == []


def test_zoho_recruit_parser_honors_zero_max_jobs() -> None:
    """A non-positive max_jobs must yield no candidates."""

    adapter = ZohoRecruitAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://acme.zohorecruit.com/jobs/Careers",
        ZOHO_RECRUIT_SAMPLE_HTML,
        max_jobs=0,
    )

    assert jobs == []


def test_zoho_recruit_parser_deduplicates_and_honors_limit() -> None:
    """Duplicate posting URLs should be returned once and respect max_jobs."""

    adapter = ZohoRecruitAdapter(user_agent="test-agent")
    html = """
    <div class="job">
      <a href="/jobs/Careers?jobId=ZR-1001">First Role</a>
      <span class="job-location">Austin</span>
    </div>
    <div class="job">
      <a href="/jobs/Careers?jobId=ZR-1001">First Role Duplicate</a>
      <span class="job-location">Austin</span>
    </div>
    <div class="job">
      <a href="/jobs/Careers?jobId=ZR-1002">Second Role</a>
      <span class="job-location">Remote</span>
    </div>
    """
    jobs = adapter._parse_html("https://acme.zohorecruit.com/jobs/Careers", html, max_jobs=1)

    assert len(jobs) == 1
    assert jobs[0].title == "First Role"
    assert jobs[0].external_id == "ZR-1001"


def test_zoho_recruit_location_is_scoped_to_its_posting() -> None:
    """A posting without its own location must not inherit a sibling's location."""

    adapter = ZohoRecruitAdapter(user_agent="test-agent")
    html = """
    <div class="job">
      <a href="/job/1001"><h4>First Role</h4></a>
    </div>
    <div class="job">
      <a href="/job/1002"><h4>Second Role</h4></a>
      <span class="job-location">Austin</span>
    </div>
    """
    jobs = adapter._parse_html("https://acme.zohorecruit.com/jobs/Careers", html, max_jobs=10)

    by_title = {job.title: job for job in jobs}
    assert by_title["First Role"].location is None
    assert by_title["Second Role"].location == "Austin"

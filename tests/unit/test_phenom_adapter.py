"""Unit tests for the Phenom People careers site adapter."""

from __future__ import annotations

from autoapply_agent.adapters.phenom import PhenomPeopleAdapter

PHENOM_SAMPLE_HTML = """
<html>
  <body>
    <section class="jobs-list">
      <article class="job">
        <a href="/job/PHENOM-1234/platform-engineer">Platform Engineer</a>
        <span class="job-location">Austin, TX</span>
      </article>
      <article class="job">
        <a href="/jobs/987654" title="Data Engineer"></a>
        <span class="job-location">Remote</span>
      </article>
      <article class="posting">
        <a href="https://careers.example.com/us/en/job/R_7788/site-reliability-engineer">
          Site Reliability Engineer
        </a>
        <span class="posting-location">New York, NY</span>
      </article>
    </section>
    <a href="/jobs">All jobs</a>
    <a href="/job/index">Job index</a>
    <a href="/job/PHENOM-1234/platform-engineer/apply">Apply</a>
    <a href="/login">Login</a>
  </body>
</html>
"""


def test_phenom_parser_extracts_posting_anchors() -> None:
    """Phenom parser should extract posting fields and skip navigation links."""

    adapter = PhenomPeopleAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://careers.example.com/us/en/search-results",
        PHENOM_SAMPLE_HTML,
        max_jobs=10,
    )

    by_title = {job.title: job for job in jobs}
    assert set(by_title) == {
        "Platform Engineer",
        "Data Engineer",
        "Site Reliability Engineer",
    }
    assert by_title["Platform Engineer"].external_id == "PHENOM-1234"
    assert by_title["Platform Engineer"].location == "Austin, TX"
    assert by_title["Platform Engineer"].url == (
        "https://careers.example.com/job/PHENOM-1234/platform-engineer"
    )
    assert by_title["Platform Engineer"].company == "careers.example.com"
    assert by_title["Platform Engineer"].raw == {"source": "phenom"}
    assert by_title["Data Engineer"].external_id == "987654"
    assert by_title["Data Engineer"].location == "Remote"
    assert by_title["Data Engineer"].url == "https://careers.example.com/jobs/987654"
    assert by_title["Site Reliability Engineer"].external_id == "R_7788"
    assert by_title["Site Reliability Engineer"].location == "New York, NY"


def test_phenom_accepts_supported_detail_shapes() -> None:
    """Phenom postings may use ``/job/{id}/{slug}`` or ``/jobs/{id}`` paths."""

    assert PhenomPeopleAdapter._extract_external_id("/job/PHENOM-1001/platform-engineer") == (
        "PHENOM-1001"
    )
    assert PhenomPeopleAdapter._extract_external_id("/jobs/9001") == "9001"
    assert PhenomPeopleAdapter._extract_external_id("/us/en/job/R_7788/sre") == "R_7788"


def test_phenom_anchor_title_falls_back_to_title_attribute() -> None:
    """Empty-text Phenom anchors with a title= attribute must be kept."""

    adapter = PhenomPeopleAdapter(user_agent="test-agent")
    html = """
    <div class="job">
      <a href="/jobs/7777" title="Staff Platform Engineer"></a>
      <span class="job-location">Remote</span>
    </div>
    """
    jobs = adapter._parse_html("https://careers.example.com/search-results", html, max_jobs=10)

    assert len(jobs) == 1
    assert jobs[0].title == "Staff Platform Engineer"
    assert jobs[0].external_id == "7777"
    assert jobs[0].location == "Remote"


def test_phenom_parser_rejects_list_index_login_and_apply_links() -> None:
    """List/index/login/apply-step links must not become candidates."""

    adapter = PhenomPeopleAdapter(user_agent="test-agent")
    nav_only_html = """
    <a href="/jobs">Jobs list</a>
    <a href="/jobs/list">Jobs list page</a>
    <a href="/job/index">Job index</a>
    <a href="/job/PHENOM-1234/platform-engineer/apply">Apply path</a>
    <a href="/job/PHENOM-1234/platform-engineer?mode=apply">Apply query</a>
    <a href="/jobs/PHENOM-1234/login">Login path</a>
    <a href="/search-results">Search results</a>
    """
    jobs = adapter._parse_html(
        "https://careers.example.com/search-results",
        nav_only_html,
        max_jobs=10,
    )

    assert jobs == []


def test_phenom_parser_honors_zero_max_jobs() -> None:
    """A non-positive max_jobs must yield no candidates."""

    adapter = PhenomPeopleAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://careers.example.com/search-results",
        PHENOM_SAMPLE_HTML,
        max_jobs=0,
    )

    assert jobs == []


def test_phenom_parser_deduplicates_and_honors_limit() -> None:
    """Duplicate posting URLs should be returned once and respect max_jobs."""

    adapter = PhenomPeopleAdapter(user_agent="test-agent")
    html = """
    <div class="job">
      <a href="/job/PHENOM-1001/first-role">First Role</a>
      <span class="job-location">Austin</span>
    </div>
    <div class="job">
      <a href="/job/PHENOM-1001/first-role">First Role Duplicate</a>
      <span class="job-location">Austin</span>
    </div>
    <div class="job">
      <a href="/jobs/PHENOM-1002">Second Role</a>
      <span class="job-location">Remote</span>
    </div>
    """
    jobs = adapter._parse_html("https://careers.example.com/search-results", html, max_jobs=1)

    assert len(jobs) == 1
    assert jobs[0].title == "First Role"
    assert jobs[0].external_id == "PHENOM-1001"


def test_phenom_location_is_scoped_to_its_posting() -> None:
    """A posting without its own location must not inherit a sibling's location."""

    adapter = PhenomPeopleAdapter(user_agent="test-agent")
    html = """
    <div class="job">
      <a href="/job/1001/first-role"><h4>First Role</h4></a>
    </div>
    <div class="job">
      <a href="/job/1002/second-role"><h4>Second Role</h4></a>
      <span class="job-location">Austin</span>
    </div>
    """
    jobs = adapter._parse_html("https://careers.example.com/search-results", html, max_jobs=10)

    by_title = {job.title: job for job in jobs}
    assert by_title["First Role"].location is None
    assert by_title["Second Role"].location == "Austin"

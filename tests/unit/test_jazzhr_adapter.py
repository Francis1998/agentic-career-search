"""Unit tests for the JazzHR careers portal adapter."""

from __future__ import annotations

from autoapply_agent.adapters.jazzhr import JazzHrAdapter

JAZZHR_SAMPLE_HTML = """
<html>
  <body>
    <section class="jobs-list">
      <article class="job">
        <h3>
          <a href="/apply/JAZZ-1234">
            Platform Engineer
          </a>
        </h3>
        <span class="job-location">Austin, TX</span>
      </article>
      <article class="job">
        <h3>
          <a href="/apply/JAZZ_7788/site-reliability-engineer"
             title="Site Reliability Engineer"></a>
        </h3>
        <span class="job-location">Remote</span>
      </article>
      <article class="job">
        <h3>
          <a href="https://acme.applytojob.com/apply/9001/data-engineer">Data Engineer</a>
        </h3>
        <span class="job-location">New York, NY</span>
      </article>
    </section>
    <a href="/apply">Open roles</a>
    <a href="/apply/search">Search</a>
    <a href="/jobs/JAZZ-1234">Legacy jobs page</a>
    <a href="/about">About</a>
  </body>
</html>
"""


def test_jazzhr_parser_extracts_jobs() -> None:
    """JazzHR parser should extract posting fields and skip navigation links."""

    adapter = JazzHrAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://acme.applytojob.com/apply",
        JAZZHR_SAMPLE_HTML,
        max_jobs=10,
    )

    by_title = {job.title: job for job in jobs}
    assert set(by_title) == {
        "Platform Engineer",
        "Site Reliability Engineer",
        "Data Engineer",
    }
    assert by_title["Platform Engineer"].external_id == "JAZZ-1234"
    assert by_title["Platform Engineer"].location == "Austin, TX"
    assert by_title["Platform Engineer"].url == "https://acme.applytojob.com/apply/JAZZ-1234"
    assert by_title["Platform Engineer"].company == "acme.applytojob.com"
    assert by_title["Platform Engineer"].raw == {"source": "jazzhr"}
    assert by_title["Site Reliability Engineer"].external_id == "JAZZ_7788"
    assert by_title["Site Reliability Engineer"].location == "Remote"
    assert by_title["Site Reliability Engineer"].url.endswith(
        "/apply/JAZZ_7788/site-reliability-engineer"
    )
    assert by_title["Data Engineer"].external_id == "9001"
    assert by_title["Data Engineer"].location == "New York, NY"


def test_jazzhr_accepts_id_only_and_slug_posting_urls() -> None:
    """JazzHR posting links may be ``/apply/{id}`` or ``/apply/{id}/{slug}``."""

    assert JazzHrAdapter._extract_external_id("/apply/JAZZ-1001") == "JAZZ-1001"
    assert (
        JazzHrAdapter._extract_external_id("/apply/JAZZ_1002/senior-platform-engineer")
        == "JAZZ_1002"
    )


def test_jazzhr_anchor_title_falls_back_to_title_attribute() -> None:
    """Empty-text JazzHR anchors with a title= attribute must be kept."""

    adapter = JazzHrAdapter(user_agent="test-agent")
    html = """
    <div class="job">
      <a href="/apply/JAZZ-7777/staff-platform-engineer" title="Staff Platform Engineer"></a>
      <span class="job-location">Remote</span>
    </div>
    """
    jobs = adapter._parse_html("https://acme.applytojob.com/apply", html, max_jobs=10)

    assert len(jobs) == 1
    assert jobs[0].title == "Staff Platform Engineer"
    assert jobs[0].external_id == "JAZZ-7777"
    assert jobs[0].location == "Remote"


def test_jazzhr_parser_ignores_non_posting_links() -> None:
    """Apply root, search pages, deeper paths, and nav links are not postings."""

    adapter = JazzHrAdapter(user_agent="test-agent")
    nav_only_html = """
    <a href="/apply">Apply index</a>
    <a href="/apply/search">Search</a>
    <a href="/apply/login">Login</a>
    <a href="/apply/JAZZ-1234/details/extra">Deeper path</a>
    <a href="/jobs/JAZZ-1234">Legacy jobs path</a>
    <a href="/about">About</a>
    """
    jobs = adapter._parse_html(
        "https://acme.applytojob.com/apply",
        nav_only_html,
        max_jobs=10,
    )

    assert jobs == []


def test_jazzhr_parser_honors_zero_max_jobs() -> None:
    """A non-positive max_jobs must yield no candidates."""

    adapter = JazzHrAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://acme.applytojob.com/apply",
        JAZZHR_SAMPLE_HTML,
        max_jobs=0,
    )

    assert jobs == []


def test_jazzhr_parser_deduplicates_and_honors_limit() -> None:
    """Duplicate posting URLs should be returned once and respect max_jobs."""

    adapter = JazzHrAdapter(user_agent="test-agent")
    html = """
    <div class="job">
      <a href="/apply/JAZZ-1001/first-role">First Role</a>
      <span class="job-location">Austin</span>
    </div>
    <div class="job">
      <a href="/apply/JAZZ-1001/first-role">First Role Duplicate</a>
      <span class="job-location">Austin</span>
    </div>
    <div class="job">
      <a href="/apply/JAZZ-1002/second-role">Second Role</a>
      <span class="job-location">Remote</span>
    </div>
    """
    jobs = adapter._parse_html("https://acme.applytojob.com/apply", html, max_jobs=1)

    assert len(jobs) == 1
    assert jobs[0].title == "First Role"
    assert jobs[0].external_id == "JAZZ-1001"


def test_jazzhr_location_is_scoped_to_its_posting() -> None:
    """A posting without its own location must not inherit a sibling's location."""

    adapter = JazzHrAdapter(user_agent="test-agent")
    html = """
    <div class="job">
      <a href="/apply/1001/first-role"><h4>First Role</h4></a>
    </div>
    <div class="job">
      <a href="/apply/1002/second-role"><h4>Second Role</h4></a>
      <span class="job-location">Austin</span>
    </div>
    """
    jobs = adapter._parse_html("https://acme.applytojob.com/apply", html, max_jobs=10)

    by_title = {job.title: job for job in jobs}
    assert by_title["First Role"].location is None
    assert by_title["Second Role"].location == "Austin"

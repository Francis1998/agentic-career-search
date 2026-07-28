"""Unit tests for the Rippling careers site adapter."""

from __future__ import annotations

from autoapply_agent.adapters.rippling import RipplingAdapter

RIPPLING_SAMPLE_HTML = """
<html>
  <body>
    <section class="openings">
      <article class="job">
        <a href="/acme/jobs/5b74a69a-2353-4812-bd7d-ecc8b73c23ee">
          Senior Backend Engineer
        </a>
        <span class="job-location">San Francisco, CA</span>
      </article>
      <article class="job">
        <a href="https://ats.rippling.com/acme/jobs/75804d93-747e-41e4-89fc-26d7c16026bb?jobSite=LinkedIn">
          Product Manager
        </a>
        <span class="job-location">Remote (US)</span>
      </article>
    </section>
    <a href="/acme/jobs">All roles</a>
    <a href="/acme/jobs/5b74a69a-2353-4812-bd7d-ecc8b73c23ee/apply">Apply</a>
    <a href="https://www.rippling.com/careers">Company careers</a>
  </body>
</html>
"""


def test_rippling_parser_extracts_jobs() -> None:
    """Rippling parser should extract posting fields and skip board links."""

    adapter = RipplingAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://ats.rippling.com/acme/jobs",
        RIPPLING_SAMPLE_HTML,
        max_jobs=10,
    )

    by_title = {job.title: job for job in jobs}
    assert set(by_title) == {"Senior Backend Engineer", "Product Manager"}
    assert by_title["Senior Backend Engineer"].external_id == "5b74a69a-2353-4812-bd7d-ecc8b73c23ee"
    assert by_title["Senior Backend Engineer"].location == "San Francisco, CA"
    assert by_title["Senior Backend Engineer"].url == (
        "https://ats.rippling.com/acme/jobs/5b74a69a-2353-4812-bd7d-ecc8b73c23ee"
    )
    assert by_title["Product Manager"].external_id == "75804d93-747e-41e4-89fc-26d7c16026bb"
    assert by_title["Product Manager"].location == "Remote (US)"
    assert by_title["Product Manager"].url.endswith(
        "/acme/jobs/75804d93-747e-41e4-89fc-26d7c16026bb?jobSite=LinkedIn"
    )


def test_rippling_parser_ignores_non_posting_links() -> None:
    """Only terminal Rippling ``jobs/{uuid}`` detail links become candidates."""

    adapter = RipplingAdapter(user_agent="test-agent")
    nav_only_html = """
    <a href="/acme/jobs">Open roles</a>
    <a href="/acme/jobs/5b74a69a-2353-4812-bd7d-ecc8b73c23ee/apply">Apply</a>
    <a href="/careers">Careers</a>
    <a href="https://example.com/acme/jobs/75804d93-747e-41e4-89fc-26d7c16026bb">
      External board
    </a>
    """
    jobs = adapter._parse_html(
        "https://ats.rippling.com/acme/jobs",
        nav_only_html,
        max_jobs=10,
    )

    assert jobs == []


def test_rippling_parser_falls_back_to_title_attribute() -> None:
    """Icon-only posting anchors should still yield a title attribute."""

    adapter = RipplingAdapter(user_agent="test-agent")
    html = """
    <div class="job">
      <a href="/acme/jobs/deadbeef-dead-beef-dead-beefdeadbeef"
         title="Staff Platform Engineer"></a>
      <span class="job-location">New York, NY</span>
    </div>
    """
    jobs = adapter._parse_html("https://ats.rippling.com/acme/jobs", html, max_jobs=10)

    assert len(jobs) == 1
    assert jobs[0].external_id == "deadbeef-dead-beef-dead-beefdeadbeef"
    assert jobs[0].title == "Staff Platform Engineer"
    assert jobs[0].location == "New York, NY"


def test_rippling_parser_honors_zero_max_jobs() -> None:
    """A non-positive max_jobs must yield no candidates."""

    adapter = RipplingAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://ats.rippling.com/acme/jobs",
        RIPPLING_SAMPLE_HTML,
        max_jobs=0,
    )

    assert jobs == []


def test_rippling_location_is_scoped_to_its_posting() -> None:
    """A posting without its own location must not inherit a sibling's location."""

    adapter = RipplingAdapter(user_agent="test-agent")
    html = """
    <div class="job">
      <a href="/acme/jobs/11111111-2222-3333-4444-555555555555"><h4>First Role</h4></a>
    </div>
    <div class="job">
      <a href="/acme/jobs/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"><h4>Second Role</h4></a>
      <span class="job-location">London, UK</span>
    </div>
    """
    jobs = adapter._parse_html("https://ats.rippling.com/acme/jobs", html, max_jobs=10)

    by_title = {job.title: job for job in jobs}
    assert by_title["First Role"].location is None
    assert by_title["Second Role"].location == "London, UK"

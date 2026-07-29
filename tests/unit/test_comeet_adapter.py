"""Unit tests for the Comeet careers site adapter."""

from __future__ import annotations

from autoapply_agent.adapters.comeet import ComeetAdapter

_JOB_A = "550e8400-e29b-41d4-a716-446655440000"
_JOB_B = "7dcb7727-4fe1-47d6-bb17-82636428b228"
_JOB_C = "a1b2c3d4e5f6"
_PATH_A = f"/jobs/acme/abc123/senior-infra/{_JOB_A}"
_PATH_B = f"https://www.comeet.com/jobs/acme/abc123/platform-eng/{_JOB_B}"
_PATH_C = f"/jobs/acme/abc123/csm/{_JOB_C}"

COMEET_SAMPLE_HTML = f"""
<html>
  <body>
    <section class="openings">
      <article class="job">
        <a href="{_PATH_A}"
           class="heading"
           data-location="Remote">
          Senior Infrastructure Engineer
        </a>
      </article>
      <article class="job">
        <a href="{_PATH_B}"
           class="heading"
           data-location="Poland">
          Platform Engineer
        </a>
      </article>
      <article class="job">
        <a href="{_PATH_C}"
           class="heading"
           data-job-location="London, UK">
          Customer Success Manager
        </a>
      </article>
    </section>
    <a href="/jobs/acme/abc123">All jobs</a>
    <a href="{_PATH_A}/apply">Apply</a>
    <a href="/about">About</a>
  </body>
</html>
"""


def test_comeet_parser_extracts_jobs() -> None:
    """Comeet parser should extract posting fields and skip nav/apply links."""

    adapter = ComeetAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://www.comeet.co/careers/acme",
        COMEET_SAMPLE_HTML,
        max_jobs=10,
    )

    by_title = {job.title: job for job in jobs}
    assert set(by_title) == {
        "Senior Infrastructure Engineer",
        "Platform Engineer",
        "Customer Success Manager",
    }
    assert by_title["Senior Infrastructure Engineer"].external_id == _JOB_A
    assert by_title["Senior Infrastructure Engineer"].location == "Remote"
    assert by_title["Senior Infrastructure Engineer"].url == (
        f"https://www.comeet.co{_PATH_A}"
    )
    assert by_title["Platform Engineer"].external_id == _JOB_B
    assert by_title["Platform Engineer"].location == "Poland"
    assert by_title["Customer Success Manager"].external_id == _JOB_C
    assert by_title["Customer Success Manager"].location == "London, UK"
    assert by_title["Customer Success Manager"].url.endswith(_PATH_C)


def test_comeet_parser_ignores_non_posting_links() -> None:
    """Only Comeet detail links should become candidates."""

    adapter = ComeetAdapter(user_agent="test-agent")
    nav_only_html = f"""
    <a href="/jobs/acme/abc123">All jobs</a>
    <a href="{_PATH_A}/apply">Apply</a>
    <a href="/jobs/acme/abc123/platform-eng/application">Application</a>
    <a href="/about">About</a>
    <a href="/login">Login</a>
    """
    jobs = adapter._parse_html(
        "https://www.comeet.co/careers/acme",
        nav_only_html,
        max_jobs=10,
    )

    assert jobs == []


def test_comeet_parser_falls_back_to_title_attribute() -> None:
    """Icon-only posting anchors should still yield a title attribute."""

    adapter = ComeetAdapter(user_agent="test-agent")
    job_id = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    html = f"""
    <div class="job">
      <a href="/jobs/acme/abc123/staff-platform/{job_id}"
         title="Staff Platform Engineer"
         data-remote="true"></a>
    </div>
    """
    jobs = adapter._parse_html("https://www.comeet.co/careers/acme", html, max_jobs=10)

    assert len(jobs) == 1
    assert jobs[0].external_id == job_id
    assert jobs[0].title == "Staff Platform Engineer"
    assert jobs[0].location == "Remote"


def test_comeet_parser_honors_zero_max_jobs() -> None:
    """A non-positive max_jobs must yield no candidates."""

    adapter = ComeetAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://www.comeet.co/careers/acme",
        COMEET_SAMPLE_HTML,
        max_jobs=0,
    )

    assert jobs == []


def test_comeet_location_is_scoped_to_its_posting() -> None:
    """A posting without its own location must not inherit a sibling's location."""

    adapter = ComeetAdapter(user_agent="test-agent")
    html = """
    <div class="job">
      <a href="/jobs/acme/abc123/first-role/11111111-1111-1111-1111-111111111111">
        <h4>First Role</h4>
      </a>
    </div>
    <div class="job">
      <a href="/jobs/acme/abc123/second-role/22222222-2222-2222-2222-222222222222">
        <h4>Second Role</h4>
      </a>
      <span class="job-location">Berlin</span>
    </div>
    """
    jobs = adapter._parse_html("https://www.comeet.co/careers/acme", html, max_jobs=10)

    by_title = {job.title: job for job in jobs}
    assert by_title["First Role"].location is None
    assert by_title["Second Role"].location == "Berlin"


def test_comeet_parser_deduplicates_urls() -> None:
    """Duplicate posting anchors must collapse to a single candidate."""

    adapter = ComeetAdapter(user_agent="test-agent")
    html = f"""
    <a href="{_PATH_A}">Engineer</a>
    <a href="{_PATH_A}">Engineer again</a>
    """
    jobs = adapter._parse_html("https://www.comeet.co/careers/acme", html, max_jobs=10)

    assert len(jobs) == 1
    assert jobs[0].title == "Engineer"

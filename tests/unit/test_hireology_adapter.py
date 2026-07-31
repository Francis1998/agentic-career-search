"""Unit tests for the Hireology careers site adapter."""

from __future__ import annotations

from autoapply_agent.adapters.hireology import HireologyAdapter

_JOB_A = "48291"
_JOB_B = "55902"
_JOB_C = "61033"
_JOB_D = "72144"
_PATH_A = f"/jobs/{_JOB_A}"
_PATH_B = f"/careers/job/{_JOB_B}"
_PATH_C = f"/job/{_JOB_C}/software-engineer"
_PATH_D = f"/jobs/{_JOB_D}"

HIREOLOGY_SAMPLE_HTML = f"""
<html>
  <body>
    <section class="openings">
      <article class="job">
        <a href="{_PATH_A}"
           class="heading"
           data-location="Remote">
          Software Engineer
        </a>
      </article>
      <article class="job">
        <a href="{_PATH_B}"
           class="heading"
           data-location="Denver">
          Platform Engineer
        </a>
      </article>
      <article class="job">
        <a href="{_PATH_C}"
           class="heading"
           data-job-location="Denver • Remote">
          Implementation Engineer
        </a>
      </article>
      <article class="job">
        <a href="{_PATH_D}"
           class="heading"
           data-location="Austin">
          Data Engineer
        </a>
      </article>
    </section>
    <a href="/careers">All jobs</a>
    <a href="/jobs">Jobs index</a>
    <a href="{_PATH_A}/apply">Apply</a>
    <a href="/about">About</a>
  </body>
</html>
"""


def test_hireology_parser_extracts_jobs() -> None:
    """Hireology parser should extract posting fields and skip nav/apply links."""

    adapter = HireologyAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://careers.hireology.com/acme",
        HIREOLOGY_SAMPLE_HTML,
        max_jobs=10,
    )

    by_title = {job.title: job for job in jobs}
    assert set(by_title) == {
        "Software Engineer",
        "Platform Engineer",
        "Implementation Engineer",
        "Data Engineer",
    }
    assert by_title["Software Engineer"].external_id == _JOB_A
    assert by_title["Software Engineer"].location == "Remote"
    assert by_title["Software Engineer"].url == "https://careers.hireology.com/jobs/48291"
    assert by_title["Platform Engineer"].external_id == _JOB_B
    assert by_title["Platform Engineer"].location == "Denver"
    assert by_title["Implementation Engineer"].external_id == _JOB_C
    assert by_title["Implementation Engineer"].location == "Denver • Remote"
    assert by_title["Data Engineer"].external_id == _JOB_D


def test_hireology_parser_ignores_non_posting_links() -> None:
    """Only Hireology detail links should become candidates."""

    adapter = HireologyAdapter(user_agent="test-agent")
    nav_only_html = f"""
    <a href="/careers">All jobs</a>
    <a href="/jobs">Jobs index</a>
    <a href="/careers/job">Board index</a>
    <a href="{_PATH_A}/apply">Apply</a>
    <a href="/jobs/{_JOB_A}/login">Login</a>
    <a href="/about">About</a>
    <a href="/login">Login home</a>
    """
    jobs = adapter._parse_html(
        "https://careers.hireology.com/acme",
        nav_only_html,
        max_jobs=10,
    )

    assert jobs == []


def test_hireology_parser_falls_back_to_title_attribute() -> None:
    """Icon-only posting anchors should still yield a title attribute."""

    adapter = HireologyAdapter(user_agent="test-agent")
    job_id = "105577"
    html = f"""
    <div class="job">
      <a href="/jobs/{job_id}"
         title="Senior Software Engineer, Backend"
         data-remote="true"></a>
    </div>
    """
    jobs = adapter._parse_html(
        "https://careers.hireology.com/acme",
        html,
        max_jobs=10,
    )

    assert len(jobs) == 1
    assert jobs[0].external_id == job_id
    assert jobs[0].title == "Senior Software Engineer, Backend"
    assert jobs[0].location == "Remote"


def test_hireology_parser_honors_zero_max_jobs() -> None:
    """A non-positive max_jobs must yield no candidates."""

    adapter = HireologyAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://careers.hireology.com/acme",
        HIREOLOGY_SAMPLE_HTML,
        max_jobs=0,
    )

    assert jobs == []


def test_hireology_location_is_scoped_to_its_posting() -> None:
    """A posting without its own location must not inherit a sibling's location."""

    adapter = HireologyAdapter(user_agent="test-agent")
    html = """
    <div class="job">
      <a href="/jobs/11111"><h4>First Role</h4></a>
    </div>
    <div class="job">
      <a href="/careers/job/22222"><h4>Second Role</h4></a>
      <span class="job-location">Berlin</span>
    </div>
    """
    jobs = adapter._parse_html(
        "https://careers.hireology.com/acme",
        html,
        max_jobs=10,
    )

    by_title = {job.title: job for job in jobs}
    assert by_title["First Role"].location is None
    assert by_title["Second Role"].location == "Berlin"

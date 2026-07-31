"""Unit tests for the Homerun careers site adapter."""

from __future__ import annotations

from autoapply_agent.adapters.homerun import HomerunAdapter

_JOB_A = "48291"
_JOB_B = "55902"
_JOB_C = "61033"
_PATH_A = f"/jobs/{_JOB_A}-software-engineer"
_PATH_B = f"/o/{_JOB_B}"
_PATH_C = f"/vacancies/{_JOB_C}"

HOMERUN_SAMPLE_HTML = f"""
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
        <a href="/vacancy/{_JOB_A}"
           class="heading"
           data-location="Austin">
          Data Engineer
        </a>
      </article>
    </section>
    <a href="/jobs">All jobs</a>
    <a href="/vacancies">Vacancies index</a>
    <a href="{_PATH_A}/apply">Apply</a>
    <a href="/about">About</a>
  </body>
</html>
"""


def test_homerun_parser_extracts_jobs() -> None:
    """Homerun parser should extract posting fields and skip nav/apply links."""

    adapter = HomerunAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://acme.homerun.co",
        HOMERUN_SAMPLE_HTML,
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
    assert by_title["Software Engineer"].url.endswith(_PATH_A)
    assert by_title["Platform Engineer"].external_id == _JOB_B
    assert by_title["Platform Engineer"].location == "Denver"
    assert by_title["Implementation Engineer"].external_id == _JOB_C
    assert by_title["Implementation Engineer"].location == "Denver • Remote"
    assert by_title["Data Engineer"].external_id == _JOB_A


def test_homerun_parser_ignores_non_posting_links() -> None:
    """Only Homerun detail links should become candidates."""

    adapter = HomerunAdapter(user_agent="test-agent")
    nav_only_html = f"""
    <a href="/jobs">All jobs</a>
    <a href="/vacancies">Vacancies index</a>
    <a href="/o">Openings index</a>
    <a href="{_PATH_A}/apply">Apply</a>
    <a href="/jobs/{_JOB_A}-software-engineer/login">Login</a>
    <a href="/about">About</a>
    <a href="/login">Login home</a>
    """
    jobs = adapter._parse_html(
        "https://acme.homerun.co",
        nav_only_html,
        max_jobs=10,
    )

    assert jobs == []


def test_homerun_parser_falls_back_to_title_attribute() -> None:
    """Icon-only posting anchors should still yield a title attribute."""

    adapter = HomerunAdapter(user_agent="test-agent")
    job_id = "105577"
    html = f"""
    <div class="job">
      <a href="/jobs/{job_id}-senior-backend-engineer"
         title="Senior Software Engineer, Backend"
         data-remote="true"></a>
    </div>
    """
    jobs = adapter._parse_html(
        "https://acme.homerun.co",
        html,
        max_jobs=10,
    )

    assert len(jobs) == 1
    assert jobs[0].external_id == job_id
    assert jobs[0].title == "Senior Software Engineer, Backend"
    assert jobs[0].location == "Remote"


def test_homerun_parser_honors_zero_max_jobs() -> None:
    """A non-positive max_jobs must yield no candidates."""

    adapter = HomerunAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://acme.homerun.co",
        HOMERUN_SAMPLE_HTML,
        max_jobs=0,
    )

    assert jobs == []


def test_homerun_location_is_scoped_to_its_posting() -> None:
    """A posting without its own location must not inherit a sibling's location."""

    adapter = HomerunAdapter(user_agent="test-agent")
    html = """
    <div class="job">
      <a href="/jobs/11111-first-role"><h4>First Role</h4></a>
    </div>
    <div class="job">
      <a href="/vacancies/22222"><h4>Second Role</h4></a>
      <span class="job-location">Berlin</span>
    </div>
    """
    jobs = adapter._parse_html(
        "https://acme.homerun.co",
        html,
        max_jobs=10,
    )

    by_title = {job.title: job for job in jobs}
    assert by_title["First Role"].location is None
    assert by_title["Second Role"].location == "Berlin"

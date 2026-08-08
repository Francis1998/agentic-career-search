"""Unit tests for the Jobylon careers site adapter."""

from __future__ import annotations

from autoapply_agent.adapters.jobylon import JobylonAdapter

_JOB_A = "48291"
_JOB_B = "55902"
_JOB_C = "61033"
_JOB_D = "72044"
_JOB_E = "83055"
_JOB_F = "94066"
_PATH_A = f"/jobs/{_JOB_A}"
_PATH_B = f"/job/{_JOB_B}"
_PATH_C = f"/careers/{_JOB_C}"
_PATH_D = f"/careers/job/{_JOB_D}"
_PATH_E = f"/positions/{_JOB_E}"
_PATH_F = f"/vacancies/{_JOB_F}"

JOBYLON_SAMPLE_HTML = f"""
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
           data-location="San Francisco">
          Platform Engineer
        </a>
      </article>
      <article class="job">
        <a href="{_PATH_C}"
           class="heading"
           data-job-location="New York">
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
      <article class="job">
        <a href="{_PATH_E}"
           class="heading"
           data-location="Seattle">
          Product Manager
        </a>
      </article>
      <article class="job">
        <a href="{_PATH_F}"
           class="heading"
           data-location="Stockholm">
          Customer Success Manager
        </a>
      </article>
    </section>
    <a href="/jobs">All jobs</a>
    <a href="/careers">Careers index</a>
    <a href="/positions">Positions index</a>
    <a href="/vacancies">Vacancies index</a>
    <a href="{_PATH_A}/apply">Apply</a>
    <a href="/about">About</a>
  </body>
</html>
"""


def test_jobylon_parser_extracts_jobs() -> None:
    """Jobylon parser should extract posting fields and skip nav/apply links."""

    adapter = JobylonAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://jobs.jobylon.com/companies/acme/jobs/",
        JOBYLON_SAMPLE_HTML,
        max_jobs=10,
    )

    by_title = {job.title: job for job in jobs}
    assert set(by_title) == {
        "Software Engineer",
        "Platform Engineer",
        "Implementation Engineer",
        "Data Engineer",
        "Product Manager",
        "Customer Success Manager",
    }
    assert by_title["Software Engineer"].external_id == _JOB_A
    assert by_title["Software Engineer"].location == "Remote"
    assert by_title["Software Engineer"].url.endswith(_PATH_A)
    assert by_title["Software Engineer"].raw == {"source": "jobylon"}
    assert by_title["Platform Engineer"].external_id == _JOB_B
    assert by_title["Platform Engineer"].location == "San Francisco"
    assert by_title["Implementation Engineer"].external_id == _JOB_C
    assert by_title["Implementation Engineer"].location == "New York"
    assert by_title["Data Engineer"].external_id == _JOB_D
    assert by_title["Product Manager"].external_id == _JOB_E
    assert by_title["Customer Success Manager"].external_id == _JOB_F


def test_jobylon_parser_ignores_non_posting_links() -> None:
    """Only Jobylon detail links should become candidates."""

    adapter = JobylonAdapter(user_agent="test-agent")
    nav_only_html = f"""
    <a href="/jobs">All jobs</a>
    <a href="/careers">Careers index</a>
    <a href="/positions">Positions index</a>
    <a href="/vacancies">Vacancies index</a>
    <a href="{_PATH_A}/apply">Apply</a>
    <a href="/jobs/{_JOB_A}/login">Login</a>
    <a href="/about">About</a>
    <a href="/login">Login home</a>
    """
    jobs = adapter._parse_html(
        "https://jobs.jobylon.com/companies/acme/jobs/",
        nav_only_html,
        max_jobs=10,
    )

    assert jobs == []


def test_jobylon_parser_falls_back_to_title_attribute() -> None:
    """Icon-only posting anchors should still yield a title attribute."""

    adapter = JobylonAdapter(user_agent="test-agent")
    job_id = "105577"
    html = f"""
    <div class="job">
      <a href="/jobs/{job_id}"
         title="Senior Software Engineer, Backend"
         data-remote="true"></a>
    </div>
    """
    jobs = adapter._parse_html(
        "https://jobs.jobylon.com/companies/acme/jobs/",
        html,
        max_jobs=10,
    )

    assert len(jobs) == 1
    assert jobs[0].external_id == job_id
    assert jobs[0].title == "Senior Software Engineer, Backend"
    assert jobs[0].location == "Remote"


def test_jobylon_parser_honors_zero_max_jobs() -> None:
    """A non-positive max_jobs must yield no candidates."""

    adapter = JobylonAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://jobs.jobylon.com/companies/acme/jobs/",
        JOBYLON_SAMPLE_HTML,
        max_jobs=0,
    )

    assert jobs == []


def test_jobylon_location_is_scoped_to_its_posting() -> None:
    """A posting without its own location must not inherit a sibling's location."""

    adapter = JobylonAdapter(user_agent="test-agent")
    html = """
    <div class="job">
      <a href="/jobs/11111"><h4>First Role</h4></a>
    </div>
    <div class="job">
      <a href="/vacancies/22222"><h4>Second Role</h4></a>
      <span class="job-location">Stockholm</span>
    </div>
    """
    jobs = adapter._parse_html(
        "https://jobs.jobylon.com/companies/acme/jobs/",
        html,
        max_jobs=10,
    )

    by_title = {job.title: job for job in jobs}
    assert by_title["First Role"].location is None
    assert by_title["Second Role"].location == "Stockholm"

"""Unit tests for the JobScore careers site adapter."""

from __future__ import annotations

from autoapply_agent.adapters.jobscore import JobScoreAdapter

_JOB_A = "48291"
_JOB_B = "55902"
_JOB_C = "61033"
_JOB_D = "72144"
_PATH_A = f"/careers/acme/jobs/software-engineer-{_JOB_A}"
_PATH_B = f"https://careers.jobscore.com/careers/acme/jobs/{_JOB_B}"
_PATH_C = f"/jobs/{_JOB_C}"
_PATH_D = f"/jobs/data-engineer/{_JOB_D}"

JOBSCORE_SAMPLE_HTML = f"""
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
      <article class="job">
        <a href="/position/83355"
           class="heading"
           data-location="Remote">
          Product Manager
        </a>
      </article>
      <article class="job">
        <a href="/positions/94466"
           class="heading"
           data-location="NYC">
          Account Executive
        </a>
      </article>
    </section>
    <a href="/careers/acme">All jobs</a>
    <a href="/careers/acme/jobs">Jobs index</a>
    <a href="{_PATH_A}/apply">Apply</a>
    <a href="/about">About</a>
  </body>
</html>
"""


def test_jobscore_parser_extracts_jobs() -> None:
    """JobScore parser should extract posting fields and skip nav/apply links."""

    adapter = JobScoreAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://careers.jobscore.com/careers/acme",
        JOBSCORE_SAMPLE_HTML,
        max_jobs=10,
    )

    by_title = {job.title: job for job in jobs}
    assert set(by_title) == {
        "Software Engineer",
        "Platform Engineer",
        "Implementation Engineer",
        "Data Engineer",
        "Product Manager",
        "Account Executive",
    }
    assert by_title["Software Engineer"].external_id == _JOB_A
    assert by_title["Software Engineer"].location == "Remote"
    assert by_title["Software Engineer"].url == (f"https://careers.jobscore.com{_PATH_A}")
    assert by_title["Platform Engineer"].external_id == _JOB_B
    assert by_title["Platform Engineer"].location == "Denver"
    assert by_title["Implementation Engineer"].external_id == _JOB_C
    assert by_title["Implementation Engineer"].location == "Denver • Remote"
    assert by_title["Data Engineer"].external_id == _JOB_D
    assert by_title["Data Engineer"].location == "Austin"
    assert by_title["Product Manager"].external_id == "83355"
    assert by_title["Account Executive"].external_id == "94466"


def test_jobscore_parser_ignores_non_posting_links() -> None:
    """Only JobScore detail links should become candidates."""

    adapter = JobScoreAdapter(user_agent="test-agent")
    nav_only_html = f"""
    <a href="/careers/acme">All jobs</a>
    <a href="/careers/acme/jobs">Jobs index</a>
    <a href="{_PATH_A}/apply">Apply</a>
    <a href="/jobs/{_JOB_C}/application">Application</a>
    <a href="/position/83355/apply">Apply position</a>
    <a href="/about">About</a>
    <a href="/login">Login</a>
    <a href="/signin">Sign in</a>
    """
    jobs = adapter._parse_html(
        "https://careers.jobscore.com/careers/acme",
        nav_only_html,
        max_jobs=10,
    )

    assert jobs == []


def test_jobscore_parser_falls_back_to_title_attribute() -> None:
    """Icon-only posting anchors should still yield a title attribute."""

    adapter = JobScoreAdapter(user_agent="test-agent")
    job_id = "105577"
    html = f"""
    <div class="job">
      <a href="/careers/acme/jobs/senior-backend-{job_id}"
         title="Senior Software Engineer, Backend"
         data-remote="true"></a>
    </div>
    """
    jobs = adapter._parse_html(
        "https://careers.jobscore.com/careers/acme",
        html,
        max_jobs=10,
    )

    assert len(jobs) == 1
    assert jobs[0].external_id == job_id
    assert jobs[0].title == "Senior Software Engineer, Backend"
    assert jobs[0].location == "Remote"


def test_jobscore_parser_honors_zero_max_jobs() -> None:
    """A non-positive max_jobs must yield no candidates."""

    adapter = JobScoreAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://careers.jobscore.com/careers/acme",
        JOBSCORE_SAMPLE_HTML,
        max_jobs=0,
    )

    assert jobs == []


def test_jobscore_location_is_scoped_to_its_posting() -> None:
    """A posting without its own location must not inherit a sibling's location."""

    adapter = JobScoreAdapter(user_agent="test-agent")
    html = """
    <div class="job">
      <a href="/careers/acme/jobs/first-role-11111"><h4>First Role</h4></a>
    </div>
    <div class="job">
      <a href="/positions/22222"><h4>Second Role</h4></a>
      <span class="job-location">Berlin</span>
    </div>
    """
    jobs = adapter._parse_html(
        "https://careers.jobscore.com/careers/acme",
        html,
        max_jobs=10,
    )

    by_title = {job.title: job for job in jobs}
    assert by_title["First Role"].location is None
    assert by_title["Second Role"].location == "Berlin"

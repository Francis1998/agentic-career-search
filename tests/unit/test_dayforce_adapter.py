"""Unit tests for the Dayforce careers site adapter."""

from __future__ import annotations

from autoapply_agent.adapters.dayforce import DayforceAdapter

_JOB_A = "184291"
_JOB_B = "90210"
_JOB_C = "44102"
_JOB_D = "33110"
_PATH_A = f"/JobDetail/{_JOB_A}"
_PATH_B = f"/careers/job/{_JOB_B}"
_PATH_C = f"/MyCareer/JobDetail?jobId={_JOB_C}"
_PATH_D = f"/positions/{_JOB_D}"

DAYFORCE_SAMPLE_HTML = f"""
<html>
  <body>
    <section class="openings">
      <article class="job">
        <a href="{_PATH_A}"
           class="heading"
           data-location="Remote">
          Applied AI Software Engineer
        </a>
      </article>
      <article class="job">
        <a href="{_PATH_B}"
           class="heading"
           data-location="London">
          Data Engineer
        </a>
      </article>
      <article class="job">
        <a href="{_PATH_C}"
           class="heading"
           data-job-location="Berlin • Remote">
          Implementation Engineer
        </a>
      </article>
      <article class="job">
        <a href="{_PATH_D}"
           class="heading"
           data-location="Paris">
          Solutions Architect
        </a>
      </article>
      <article class="job">
        <a href="/position/{_JOB_D}"
           class="heading"
           data-location="Madrid">
          Security Analyst
        </a>
      </article>
    </section>
    <a href="/careers">All jobs</a>
    <a href="{_PATH_A}/apply">Apply</a>
    <a href="/login">Login</a>
  </body>
</html>
"""


def test_dayforce_parser_extracts_jobs() -> None:
    """Dayforce parser should extract posting fields and skip nav/apply links."""

    adapter = DayforceAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://careers.dayforcehcm.com/acme",
        DAYFORCE_SAMPLE_HTML,
        max_jobs=20,
    )

    by_title = {job.title: job for job in jobs}
    assert set(by_title) == {
        "Applied AI Software Engineer",
        "Data Engineer",
        "Implementation Engineer",
        "Solutions Architect",
        "Security Analyst",
    }
    assert by_title["Applied AI Software Engineer"].external_id == _JOB_A
    assert by_title["Applied AI Software Engineer"].location == "Remote"
    assert by_title["Applied AI Software Engineer"].url.endswith(_PATH_A)
    assert by_title["Data Engineer"].external_id == _JOB_B
    assert by_title["Data Engineer"].location == "London"
    assert by_title["Implementation Engineer"].external_id == _JOB_C
    assert by_title["Implementation Engineer"].location == "Berlin • Remote"
    assert by_title["Solutions Architect"].external_id == _JOB_D
    assert by_title["Security Analyst"].external_id == _JOB_D


def test_dayforce_prefers_path_id_over_query() -> None:
    """Path-segment JobDetail ids should win over jobId query values."""

    adapter = DayforceAdapter(user_agent="test-agent")
    html = f"""
    <a href="/JobDetail/{_JOB_A}?jobId={_JOB_B}" data-location="Remote">
      Path Preferred Role
    </a>
    """
    jobs = adapter._parse_html(
        "https://careers.dayforcehcm.com/acme",
        html,
        max_jobs=10,
    )

    assert len(jobs) == 1
    assert jobs[0].external_id == _JOB_A


def test_dayforce_parser_ignores_non_posting_links() -> None:
    """Only Dayforce detail links should become candidates."""

    adapter = DayforceAdapter(user_agent="test-agent")
    nav_only_html = f"""
    <a href="/careers">All jobs</a>
    <a href="/positions">Positions index</a>
    <a href="/JobDetail">Board index</a>
    <a href="{_PATH_A}/apply">Apply</a>
    <a href="/JobDetail/{_JOB_A}/login">Login</a>
    <a href="/login">Login home</a>
    """
    jobs = adapter._parse_html(
        "https://careers.dayforcehcm.com/acme",
        nav_only_html,
        max_jobs=10,
    )

    assert jobs == []


def test_dayforce_parser_falls_back_to_title_attribute() -> None:
    """Icon-only posting anchors should still yield a title attribute."""

    adapter = DayforceAdapter(user_agent="test-agent")
    html = f"""
    <div class="job">
      <a href="/JobDetail/{_JOB_A}"
         title="Senior Software Engineer, Backend"
         data-remote="true"></a>
    </div>
    """
    jobs = adapter._parse_html("https://careers.dayforcehcm.com/acme", html, max_jobs=10)

    assert len(jobs) == 1
    assert jobs[0].external_id == _JOB_A
    assert jobs[0].title == "Senior Software Engineer, Backend"
    assert jobs[0].location == "Remote"


def test_dayforce_parser_honors_zero_max_jobs() -> None:
    """A non-positive max_jobs must yield no candidates."""

    adapter = DayforceAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://careers.dayforcehcm.com/acme",
        DAYFORCE_SAMPLE_HTML,
        max_jobs=0,
    )

    assert jobs == []


def test_dayforce_location_is_scoped_to_its_posting() -> None:
    """A posting without its own location must not inherit a sibling's location."""

    adapter = DayforceAdapter(user_agent="test-agent")
    html = f"""
    <div class="job">
      <a href="/JobDetail/{_JOB_A}"><h4>First Role</h4></a>
    </div>
    <div class="job">
      <a href="/positions/{_JOB_B}"><h4>Second Role</h4></a>
      <span class="job-location">Berlin</span>
    </div>
    """
    jobs = adapter._parse_html("https://careers.dayforcehcm.com/acme", html, max_jobs=10)

    by_title = {job.title: job for job in jobs}
    assert by_title["First Role"].location is None
    assert by_title["Second Role"].location == "Berlin"

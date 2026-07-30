"""Unit tests for the Avature careers site adapter."""

from __future__ import annotations

from autoapply_agent.adapters.avature import AvatureAdapter

_JOB_A = "184291"
_JOB_B = "90210"
_JOB_C = "vac-44102"
_JOB_D = "33110"
_PATH_A = f"/JobDetail/{_JOB_A}"
_PATH_B = f"/JobDetail.aspx?JobId={_JOB_B}"
_PATH_C = f"/careers/{_JOB_C}"
_PATH_D = f"/Vacancy/{_JOB_D}"

AVATURE_SAMPLE_HTML = f"""
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
        <a href="https://careers.acme.com/careers/job/{_JOB_A}"
           class="heading"
           data-location="Remote">
          Platform Engineer
        </a>
      </article>
      <article class="job">
        <a href="/careers/VacancyDetail/{_JOB_D}"
           class="heading"
           data-location="Paris">
          Solutions Architect
        </a>
      </article>
      <article class="job">
        <a href="{_PATH_D}"
           class="heading"
           data-location="Madrid">
          Security Analyst
        </a>
      </article>
      <article class="job">
        <a href="/vacancies/{_JOB_B}"
           class="heading"
           data-location="Dublin">
          Reliability Engineer
        </a>
      </article>
    </section>
    <a href="/careers">All jobs</a>
    <a href="{_PATH_A}/apply">Apply</a>
    <a href="/RegisterCandidate">Register</a>
    <a href="/about">About</a>
  </body>
</html>
"""


def test_avature_parser_extracts_jobs() -> None:
    """Avature parser should extract posting fields and skip nav/apply links."""

    adapter = AvatureAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://careers.acme.com/careers",
        AVATURE_SAMPLE_HTML,
        max_jobs=20,
    )

    by_title = {job.title: job for job in jobs}
    assert set(by_title) == {
        "Applied AI Software Engineer",
        "Data Engineer",
        "Implementation Engineer",
        "Platform Engineer",
        "Solutions Architect",
        "Security Analyst",
        "Reliability Engineer",
    }
    assert by_title["Applied AI Software Engineer"].external_id == _JOB_A
    assert by_title["Applied AI Software Engineer"].location == "Remote"
    assert by_title["Applied AI Software Engineer"].url == (f"https://careers.acme.com{_PATH_A}")
    assert by_title["Data Engineer"].external_id == _JOB_B
    assert by_title["Data Engineer"].location == "London"
    assert by_title["Implementation Engineer"].external_id == _JOB_C
    assert by_title["Implementation Engineer"].location == "Berlin • Remote"
    assert by_title["Platform Engineer"].external_id == _JOB_A
    assert by_title["Platform Engineer"].url.endswith(f"/careers/job/{_JOB_A}")
    assert by_title["Solutions Architect"].external_id == _JOB_D
    assert by_title["Security Analyst"].external_id == _JOB_D
    assert by_title["Reliability Engineer"].external_id == _JOB_B


def test_avature_prefers_path_id_over_query() -> None:
    """Path-segment JobDetail ids should win over JobId query values."""

    adapter = AvatureAdapter(user_agent="test-agent")
    html = f"""
    <a href="/JobDetail/{_JOB_A}?JobId={_JOB_B}" data-location="Remote">
      Path Preferred Role
    </a>
    """
    jobs = adapter._parse_html(
        "https://careers.acme.com/careers",
        html,
        max_jobs=10,
    )

    assert len(jobs) == 1
    assert jobs[0].external_id == _JOB_A


def test_avature_parser_ignores_non_posting_links() -> None:
    """Only Avature detail links should become candidates."""

    adapter = AvatureAdapter(user_agent="test-agent")
    nav_only_html = f"""
    <a href="/careers">All jobs</a>
    <a href="/vacancies">Vacancies</a>
    <a href="/JobDetail">Board index</a>
    <a href="{_PATH_A}/apply">Apply</a>
    <a href="/JobDetail/{_JOB_A}/login">Login</a>
    <a href="/RegisterCandidate">RegisterCandidate</a>
    <a href="/about">About</a>
    <a href="/login">Login home</a>
    """
    jobs = adapter._parse_html(
        "https://careers.acme.com/careers",
        nav_only_html,
        max_jobs=10,
    )

    assert jobs == []


def test_avature_parser_falls_back_to_title_attribute() -> None:
    """Icon-only posting anchors should still yield a title attribute."""

    adapter = AvatureAdapter(user_agent="test-agent")
    html = f"""
    <div class="job">
      <a href="/JobDetail/{_JOB_A}"
         title="Senior Software Engineer, Backend"
         data-remote="true"></a>
    </div>
    """
    jobs = adapter._parse_html("https://careers.acme.com/careers", html, max_jobs=10)

    assert len(jobs) == 1
    assert jobs[0].external_id == _JOB_A
    assert jobs[0].title == "Senior Software Engineer, Backend"
    assert jobs[0].location == "Remote"


def test_avature_parser_honors_zero_max_jobs() -> None:
    """A non-positive max_jobs must yield no candidates."""

    adapter = AvatureAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://careers.acme.com/careers",
        AVATURE_SAMPLE_HTML,
        max_jobs=0,
    )

    assert jobs == []


def test_avature_location_is_scoped_to_its_posting() -> None:
    """A posting without its own location must not inherit a sibling's location."""

    adapter = AvatureAdapter(user_agent="test-agent")
    html = f"""
    <div class="job">
      <a href="/JobDetail/{_JOB_A}"><h4>First Role</h4></a>
    </div>
    <div class="job">
      <a href="/vacancies/{_JOB_B}"><h4>Second Role</h4></a>
      <span class="job-location">Berlin</span>
    </div>
    """
    jobs = adapter._parse_html("https://careers.acme.com/careers", html, max_jobs=10)

    by_title = {job.title: job for job in jobs}
    assert by_title["First Role"].location is None
    assert by_title["Second Role"].location == "Berlin"


def test_avature_parser_deduplicates_urls() -> None:
    """Duplicate posting anchors must collapse to a single candidate."""

    adapter = AvatureAdapter(user_agent="test-agent")
    html = f"""
    <a href="{_PATH_A}">Engineer</a>
    <a href="{_PATH_A}">Engineer again</a>
    """
    jobs = adapter._parse_html("https://careers.acme.com/careers", html, max_jobs=10)

    assert len(jobs) == 1
    assert jobs[0].title == "Engineer"

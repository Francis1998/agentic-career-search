"""Unit tests for the Eightfold careers site adapter."""

from __future__ import annotations

from autoapply_agent.adapters.eightfold import EightfoldAdapter

_JOB_A = "24123"
_JOB_B = "PID-88901"
_JOB_C = "EF-48291"
_PATH_A = f"/careers/job/{_JOB_A}"
_PATH_B = f"/careers/job/{_JOB_B}/platform-engineer"
_PATH_C = f"/career_detail/{_JOB_C}"
_PATH_D = "/position/POS-1001"
_PATH_E = "/jobs/7788"

EIGHTFOLD_SAMPLE_HTML = f"""
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
        <a href="https://acme.eightfold.ai{_PATH_D}"
           class="heading"
           data-location="Austin, TX">
          Site Reliability Engineer
        </a>
      </article>
      <article class="job">
        <a href="{_PATH_E}"
           class="heading"
           data-location="New York, NY">
          Data Engineer
        </a>
      </article>
    </section>
    <a href="/careers">All jobs</a>
    <a href="{_PATH_A}/apply">Apply</a>
    <a href="/about">About</a>
    <a href="/careers?domain=acme.com&location=Remote">Facet</a>
  </body>
</html>
"""


def test_eightfold_parser_extracts_jobs() -> None:
    """Eightfold parser should extract posting fields and skip nav/apply links."""

    adapter = EightfoldAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://acme.eightfold.ai/careers",
        EIGHTFOLD_SAMPLE_HTML,
        max_jobs=10,
    )

    by_title = {job.title: job for job in jobs}
    assert set(by_title) == {
        "Applied AI Software Engineer",
        "Platform Engineer",
        "Implementation Engineer",
        "Site Reliability Engineer",
        "Data Engineer",
    }
    assert by_title["Applied AI Software Engineer"].external_id == _JOB_A
    assert by_title["Applied AI Software Engineer"].location == "Remote"
    assert by_title["Applied AI Software Engineer"].url == (f"https://acme.eightfold.ai{_PATH_A}")
    assert by_title["Applied AI Software Engineer"].raw == {"source": "eightfold"}
    assert by_title["Platform Engineer"].external_id == _JOB_B
    assert by_title["Platform Engineer"].location == "Denver"
    assert by_title["Platform Engineer"].url.endswith(_PATH_B)
    assert by_title["Implementation Engineer"].external_id == _JOB_C
    assert by_title["Implementation Engineer"].location == "Denver • Remote"
    assert by_title["Site Reliability Engineer"].external_id == "POS-1001"
    assert by_title["Site Reliability Engineer"].location == "Austin, TX"
    assert by_title["Data Engineer"].external_id == "7788"
    assert by_title["Data Engineer"].location == "New York, NY"


def test_eightfold_parser_ignores_non_posting_links() -> None:
    """Only Eightfold detail links should become candidates."""

    adapter = EightfoldAdapter(user_agent="test-agent")
    nav_only_html = f"""
    <a href="/careers">All jobs</a>
    <a href="{_PATH_A}/apply">Apply</a>
    <a href="/careers/job/{_JOB_A}/application">Application</a>
    <a href="/about">About</a>
    <a href="/login">Login</a>
    <a href="/signin">Sign in</a>
    <a href="/careers/search">Search</a>
    <a href="/careers?domain=acme.com&location=Remote&department=Engineering">Facet</a>
    <a href="/jobs">Jobs index</a>
    """
    jobs = adapter._parse_html(
        "https://acme.eightfold.ai/careers",
        nav_only_html,
        max_jobs=10,
    )

    assert jobs == []


def test_eightfold_parser_falls_back_to_title_attribute() -> None:
    """Icon-only posting anchors should still yield a title attribute."""

    adapter = EightfoldAdapter(user_agent="test-agent")
    job_id = "EF-99102"
    html = f"""
    <div class="job">
      <a href="/careers/job/{job_id}"
         title="Senior Software Engineer, Backend"
         data-remote="true"></a>
    </div>
    """
    jobs = adapter._parse_html("https://acme.eightfold.ai/careers", html, max_jobs=10)

    assert len(jobs) == 1
    assert jobs[0].external_id == job_id
    assert jobs[0].title == "Senior Software Engineer, Backend"
    assert jobs[0].location == "Remote"


def test_eightfold_parser_honors_zero_max_jobs() -> None:
    """A non-positive max_jobs must yield no candidates."""

    adapter = EightfoldAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://acme.eightfold.ai/careers",
        EIGHTFOLD_SAMPLE_HTML,
        max_jobs=0,
    )

    assert jobs == []


def test_eightfold_location_is_scoped_to_its_posting() -> None:
    """A posting without its own location must not inherit a sibling's location."""

    adapter = EightfoldAdapter(user_agent="test-agent")
    html = """
    <div class="job">
      <a href="/careers/job/1001"><h4>First Role</h4></a>
    </div>
    <div class="job">
      <a href="/position/role-22222"><h4>Second Role</h4></a>
      <span class="job-location">Berlin</span>
    </div>
    """
    jobs = adapter._parse_html("https://acme.eightfold.ai/careers", html, max_jobs=10)

    by_title = {job.title: job for job in jobs}
    assert by_title["First Role"].location is None
    assert by_title["Second Role"].location == "Berlin"


def test_eightfold_parser_deduplicates_urls() -> None:
    """Duplicate posting anchors must collapse to a single candidate."""

    adapter = EightfoldAdapter(user_agent="test-agent")
    html = f"""
    <a href="{_PATH_A}">Engineer</a>
    <a href="{_PATH_A}">Engineer again</a>
    """
    jobs = adapter._parse_html("https://acme.eightfold.ai/careers", html, max_jobs=10)

    assert len(jobs) == 1
    assert jobs[0].title == "Engineer"

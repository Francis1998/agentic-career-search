"""Unit tests for the Gem careers site adapter."""

from __future__ import annotations

from autoapply_agent.adapters.gem import GemAdapter

_JOB_A = "am9icG9zdDpFgfzkVhSJrW-sCsfQosvr"
_JOB_B = "am9icG9zdDpX2-MSo3gCxMqddEi-JunX"
_JOB_C = "opening-48291"
_PATH_A = f"/doowii/{_JOB_A}"
_PATH_B = f"https://jobs.gem.com/doowii/{_JOB_B}"
_PATH_C = f"/jobs/{_JOB_C}"

GEM_SAMPLE_HTML = f"""
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
          Data Engineer
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
        <a href="https://acme.gem.com/careers/{_JOB_A}"
           class="heading"
           data-location="Remote">
          Platform Engineer
        </a>
      </article>
    </section>
    <a href="/doowii">All jobs</a>
    <a href="{_PATH_A}/apply">Apply</a>
    <a href="/about">About</a>
  </body>
</html>
"""


def test_gem_parser_extracts_jobs() -> None:
    """Gem parser should extract posting fields and skip nav/apply links."""

    adapter = GemAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://jobs.gem.com/doowii",
        GEM_SAMPLE_HTML,
        max_jobs=10,
    )

    by_title = {job.title: job for job in jobs}
    assert set(by_title) == {
        "Applied AI Software Engineer",
        "Data Engineer",
        "Implementation Engineer",
        "Platform Engineer",
    }
    assert by_title["Applied AI Software Engineer"].external_id == _JOB_A
    assert by_title["Applied AI Software Engineer"].location == "Remote"
    assert by_title["Applied AI Software Engineer"].url == (f"https://jobs.gem.com{_PATH_A}")
    assert by_title["Data Engineer"].external_id == _JOB_B
    assert by_title["Data Engineer"].location == "Denver"
    assert by_title["Implementation Engineer"].external_id == _JOB_C
    assert by_title["Implementation Engineer"].location == "Denver • Remote"
    assert by_title["Platform Engineer"].external_id == _JOB_A
    assert by_title["Platform Engineer"].url.endswith(f"/careers/{_JOB_A}")


def test_gem_parser_ignores_non_posting_links() -> None:
    """Only Gem detail links should become candidates."""

    adapter = GemAdapter(user_agent="test-agent")
    nav_only_html = f"""
    <a href="/doowii">All jobs</a>
    <a href="{_PATH_A}/apply">Apply</a>
    <a href="/jobs/opening-48291/application">Application</a>
    <a href="/about">About</a>
    <a href="/login">Login</a>
    """
    jobs = adapter._parse_html(
        "https://jobs.gem.com/doowii",
        nav_only_html,
        max_jobs=10,
    )

    assert jobs == []


def test_gem_parser_falls_back_to_title_attribute() -> None:
    """Icon-only posting anchors should still yield a title attribute."""

    adapter = GemAdapter(user_agent="test-agent")
    job_id = "am9icG9zdDrk2MpBmo0CnVCGHKvpGUUe"
    html = f"""
    <div class="job">
      <a href="/doowii/{job_id}"
         title="Senior Software Engineer, Backend"
         data-remote="true"></a>
    </div>
    """
    jobs = adapter._parse_html("https://jobs.gem.com/doowii", html, max_jobs=10)

    assert len(jobs) == 1
    assert jobs[0].external_id == job_id
    assert jobs[0].title == "Senior Software Engineer, Backend"
    assert jobs[0].location == "Remote"


def test_gem_parser_honors_zero_max_jobs() -> None:
    """A non-positive max_jobs must yield no candidates."""

    adapter = GemAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://jobs.gem.com/doowii",
        GEM_SAMPLE_HTML,
        max_jobs=0,
    )

    assert jobs == []


def test_gem_location_is_scoped_to_its_posting() -> None:
    """A posting without its own location must not inherit a sibling's location."""

    adapter = GemAdapter(user_agent="test-agent")
    html = """
    <div class="job">
      <a href="/doowii/am9icG9zdDq0P4F9OdCj_bBblblPLmfz"><h4>First Role</h4></a>
    </div>
    <div class="job">
      <a href="/openings/role-22222"><h4>Second Role</h4></a>
      <span class="job-location">Berlin</span>
    </div>
    """
    jobs = adapter._parse_html("https://jobs.gem.com/doowii", html, max_jobs=10)

    by_title = {job.title: job for job in jobs}
    assert by_title["First Role"].location is None
    assert by_title["Second Role"].location == "Berlin"


def test_gem_parser_deduplicates_urls() -> None:
    """Duplicate posting anchors must collapse to a single candidate."""

    adapter = GemAdapter(user_agent="test-agent")
    html = f"""
    <a href="{_PATH_A}">Engineer</a>
    <a href="{_PATH_A}">Engineer again</a>
    """
    jobs = adapter._parse_html("https://jobs.gem.com/doowii", html, max_jobs=10)

    assert len(jobs) == 1
    assert jobs[0].title == "Engineer"

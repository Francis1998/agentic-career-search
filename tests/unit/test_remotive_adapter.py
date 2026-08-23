"""Unit tests for the Remotive careers site adapter."""

from __future__ import annotations

from autoapply_agent.adapters.remotive import RemotiveAdapter

_JOB_A = "48291"
_JOB_B = "55902"
_JOB_C = "61033"
_JOB_D = "72044"
_JOB_E = "83155"
_PATH_A = "/remote-jobs/48291"
_PATH_B = "/remote-job/55902"
_PATH_C = "/jobs/61033"
_PATH_D = "/job/72044"
_PATH_E = "/positions/83155"

REMOTIVE_SAMPLE_HTML = """
<html>
  <body>
    <section class="listings">
      <article class="job">
        <a href="/remote-jobs/48291" class="heading" data-location="Remote">
          Software Engineer
        </a>
      </article>
      <article class="job">
        <a href="/remote-job/55902" class="heading" data-location="Worldwide">
          Platform Engineer
        </a>
      </article>
      <article class="job">
        <a href="/jobs/61033" class="heading" data-job-location="Europe">
          Implementation Engineer
        </a>
      </article>
      <article class="job">
        <a href="/job/72044" class="heading" data-location="Americas">
          Data Engineer
        </a>
      </article>
      <article class="job">
        <a href="/positions/83155" class="heading" data-location="APAC">
          Backend Engineer
        </a>
      </article>
    </section>
    <a href="/remote-jobs">Index</a>
    <a href="/remote-job">Index</a>
    <a href="/jobs">Index</a>
    <a href="/job">Index</a>
    <a href="/positions">Index</a>
    <a href="/remote-jobs/48291/apply">Apply</a>
    <a href="/about">About</a>
    <a href="/index">Index page</a>
  </body>
</html>
"""


def test_remotive_parser_extracts_jobs() -> None:
    """Remotive parser should extract posting fields and skip nav/apply links."""

    adapter = RemotiveAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://remotive.com/",
        REMOTIVE_SAMPLE_HTML,
        max_jobs=10,
    )

    by_title = {job.title: job for job in jobs}
    assert set(by_title) == {
        "Software Engineer",
        "Platform Engineer",
        "Implementation Engineer",
        "Data Engineer",
        "Backend Engineer",
    }
    assert by_title["Software Engineer"].external_id == _JOB_A
    assert by_title["Software Engineer"].location == "Remote"
    assert by_title["Software Engineer"].url.endswith(_PATH_A)
    assert by_title["Software Engineer"].raw == {"source": "remotive"}
    assert by_title["Platform Engineer"].external_id == _JOB_B
    assert by_title["Platform Engineer"].location == "Worldwide"
    assert by_title["Implementation Engineer"].external_id == _JOB_C
    assert by_title["Implementation Engineer"].location == "Europe"
    assert by_title["Data Engineer"].external_id == _JOB_D
    assert by_title["Backend Engineer"].external_id == _JOB_E
    assert by_title["Backend Engineer"].url.endswith(_PATH_E)


def test_remotive_parser_ignores_non_posting_links() -> None:
    """Only Remotive detail links should become candidates."""

    adapter = RemotiveAdapter(user_agent="test-agent")
    nav_only_html = f"""
    <a href="/remote-jobs">Index</a>
    <a href="/remote-job">Index</a>
    <a href="/jobs">Index</a>
    <a href="/job">Index</a>
    <a href="/positions">Index</a>
    <a href="{_PATH_A}/apply">Apply</a>
    <a href="/jobs/{_JOB_A}/login">Login</a>
    <a href="/positions/{_JOB_E}/signin">Sign in</a>
    <a href="/about">About</a>
    <a href="/index">Index</a>
    <a href="/login">Login home</a>
    """
    jobs = adapter._parse_html(
        "https://remotive.com/",
        nav_only_html,
        max_jobs=10,
    )

    assert jobs == []


def test_remotive_parser_falls_back_to_title_attribute() -> None:
    """Empty anchor text should fall back to title attributes."""

    adapter = RemotiveAdapter(user_agent="test-agent")
    html = f"""
    <a href="{_PATH_A}" title="Attr Title" data-location="Remote"></a>
    <a href="{_PATH_B}" aria-label="Aria Title" data-location="Berlin"></a>
    """
    jobs = adapter._parse_html(
        "https://remotive.com/",
        html,
        max_jobs=10,
    )

    by_title = {job.title: job for job in jobs}
    assert by_title["Attr Title"].external_id == _JOB_A
    assert by_title["Attr Title"].location == "Remote"
    assert by_title["Aria Title"].external_id == _JOB_B
    assert by_title["Aria Title"].location == "Berlin"


def test_remotive_parser_respects_max_jobs() -> None:
    """Parser should stop once max_jobs candidates are collected."""

    adapter = RemotiveAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://remotive.com/",
        REMOTIVE_SAMPLE_HTML,
        max_jobs=2,
    )

    assert len(jobs) == 2


def test_remotive_parser_returns_empty_for_non_positive_max_jobs() -> None:
    """Non-positive max_jobs should short-circuit to an empty list."""

    adapter = RemotiveAdapter(user_agent="test-agent")
    assert adapter._parse_html("https://remotive.com/", REMOTIVE_SAMPLE_HTML, max_jobs=0) == []
    assert adapter._parse_html("https://remotive.com/", REMOTIVE_SAMPLE_HTML, max_jobs=-1) == []


def test_remotive_parser_uses_remote_flag() -> None:
    """data-remote=true should resolve location to Remote."""

    adapter = RemotiveAdapter(user_agent="test-agent")
    html = f"""
    <a href="{_PATH_A}" data-remote="true">Remote Role</a>
    """
    jobs = adapter._parse_html("https://remotive.com/", html, max_jobs=10)
    assert len(jobs) == 1
    assert jobs[0].location == "Remote"

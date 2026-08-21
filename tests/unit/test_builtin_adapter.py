"""Unit tests for the Built In careers site adapter."""

from __future__ import annotations

from autoapply_agent.adapters.builtin import BuiltinAdapter

_JOB_A = "48291"
_JOB_B = "55902"
_JOB_C = "61033"
_JOB_D = "72044"
_JOB_E = "83055"
_PATH_A = "/job/48291"
_PATH_B = "/jobs/55902"
_PATH_C = "/company-jobs/61033"
_PATH_D = "/careers/job/72044"
_PATH_E = "/role/83055"

BUILTIN_SAMPLE_HTML = """
<html>
  <body>
    <section class="listings">
      <article class="job">
        <a href="/job/48291" class="heading" data-location="Remote">
          Software Engineer
        </a>
      </article>
      <article class="job">
        <a href="/jobs/55902" class="heading" data-location="San Francisco">
          Platform Engineer
        </a>
      </article>
      <article class="job">
        <a href="/company-jobs/61033" class="heading" data-job-location="New York">
          Implementation Engineer
        </a>
      </article>
      <article class="job">
        <a href="/careers/job/72044" class="heading" data-location="Austin">
          Data Engineer
        </a>
      </article>
      <article class="job">
        <a href="/role/83055" class="heading" data-location="London">
          Product Manager
        </a>
      </article>
    </section>
    <a href="/job">Index</a>
    <a href="/jobs">Index</a>
    <a href="/company-jobs">Index</a>
    <a href="/careers">Index</a>
    <a href="/role">Index</a>
    <a href="/job/48291/apply">Apply</a>
    <a href="/about">About</a>
  </body>
</html>
"""


def test_builtin_parser_extracts_jobs() -> None:
    """Built In parser should extract posting fields and skip nav/apply links."""

    adapter = BuiltinAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://builtin.com/jobs/",
        BUILTIN_SAMPLE_HTML,
        max_jobs=10,
    )

    by_title = {job.title: job for job in jobs}
    assert set(by_title) == {
        "Software Engineer",
        "Platform Engineer",
        "Implementation Engineer",
        "Data Engineer",
        "Product Manager",
    }
    assert by_title["Software Engineer"].external_id == _JOB_A
    assert by_title["Software Engineer"].location == "Remote"
    assert by_title["Software Engineer"].url.endswith(_PATH_A)
    assert by_title["Software Engineer"].raw == {"source": "builtin"}
    assert by_title["Platform Engineer"].external_id == _JOB_B
    assert by_title["Platform Engineer"].location == "San Francisco"
    assert by_title["Implementation Engineer"].external_id == _JOB_C
    assert by_title["Implementation Engineer"].location == "New York"
    assert by_title["Data Engineer"].external_id == _JOB_D
    assert by_title["Product Manager"].external_id == _JOB_E


def test_builtin_parser_ignores_non_posting_links() -> None:
    """Only Built In detail links should become candidates."""

    adapter = BuiltinAdapter(user_agent="test-agent")
    nav_only_html = f"""
    <a href="/job">Index</a>
    <a href="/jobs">Index</a>
    <a href="/company-jobs">Index</a>
    <a href="/careers">Index</a>
    <a href="/role">Index</a>
    <a href="{_PATH_A}/apply">Apply</a>
    <a href="/jobs/{_JOB_A}/login">Login</a>
    <a href="/about">About</a>
    <a href="/login">Login home</a>
    """
    jobs = adapter._parse_html(
        "https://builtin.com/jobs/",
        nav_only_html,
        max_jobs=10,
    )

    assert jobs == []


def test_builtin_parser_falls_back_to_title_attribute() -> None:
    """Empty anchor text should fall back to title attributes."""

    adapter = BuiltinAdapter(user_agent="test-agent")
    html = f"""
    <a href="{_PATH_A}" title="Attr Title" data-location="Remote"></a>
    <a href="{_PATH_B}" aria-label="Aria Title" data-location="Berlin"></a>
    """
    jobs = adapter._parse_html(
        "https://builtin.com/jobs/",
        html,
        max_jobs=10,
    )

    by_title = {job.title: job for job in jobs}
    assert by_title["Attr Title"].external_id == _JOB_A
    assert by_title["Attr Title"].location == "Remote"
    assert by_title["Aria Title"].external_id == _JOB_B
    assert by_title["Aria Title"].location == "Berlin"


def test_builtin_parser_respects_max_jobs() -> None:
    """Parser should stop once max_jobs candidates are collected."""

    adapter = BuiltinAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://builtin.com/jobs/",
        BUILTIN_SAMPLE_HTML,
        max_jobs=2,
    )

    assert len(jobs) == 2


def test_builtin_parser_returns_empty_for_non_positive_max_jobs() -> None:
    """Non-positive max_jobs should short-circuit to an empty list."""

    adapter = BuiltinAdapter(user_agent="test-agent")
    assert adapter._parse_html("https://builtin.com/jobs/", BUILTIN_SAMPLE_HTML, max_jobs=0) == []
    assert adapter._parse_html("https://builtin.com/jobs/", BUILTIN_SAMPLE_HTML, max_jobs=-1) == []


def test_builtin_parser_uses_remote_flag() -> None:
    """data-remote=true should resolve location to Remote."""

    adapter = BuiltinAdapter(user_agent="test-agent")
    html = f"""
    <a href="{_PATH_A}" data-remote="true">Remote Role</a>
    """
    jobs = adapter._parse_html("https://builtin.com/jobs/", html, max_jobs=10)
    assert len(jobs) == 1
    assert jobs[0].location == "Remote"

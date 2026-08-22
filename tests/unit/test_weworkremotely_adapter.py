"""Unit tests for the WeWorkRemotely careers site adapter."""

from __future__ import annotations

from autoapply_agent.adapters.weworkremotely import WeworkremotelyAdapter

_JOB_A = "48291"
_JOB_B = "55902"
_JOB_C = "61033"
_JOB_D = "72044"
_JOB_E = "83055"
_PATH_A = "/remote-jobs/48291"
_PATH_B = "/jobs/55902"
_PATH_C = "/job/61033"
_PATH_D = "/listings/72044"
_PATH_E = "/listing/83055"

WEWORKREMOTELY_SAMPLE_HTML = """
<html>
  <body>
    <section class="listings">
      <article class="job">
        <a href="/remote-jobs/48291" class="heading" data-location="Remote">
          Software Engineer
        </a>
      </article>
      <article class="job">
        <a href="/jobs/55902" class="heading" data-location="Worldwide">
          Platform Engineer
        </a>
      </article>
      <article class="job">
        <a href="/job/61033" class="heading" data-job-location="Europe">
          Implementation Engineer
        </a>
      </article>
      <article class="job">
        <a href="/listings/72044" class="heading" data-location="Americas">
          Data Engineer
        </a>
      </article>
      <article class="job">
        <a href="/listing/83055" class="heading" data-location="London">
          Product Manager
        </a>
      </article>
    </section>
    <a href="/remote-jobs">Index</a>
    <a href="/jobs">Index</a>
    <a href="/job">Index</a>
    <a href="/listings">Index</a>
    <a href="/listing">Index</a>
    <a href="/remote-jobs/48291/apply">Apply</a>
    <a href="/about">About</a>
    <a href="/index">Index page</a>
  </body>
</html>
"""


def test_weworkremotely_parser_extracts_jobs() -> None:
    """WeWorkRemotely parser should extract posting fields and skip nav/apply links."""

    adapter = WeworkremotelyAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://weworkremotely.com/",
        WEWORKREMOTELY_SAMPLE_HTML,
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
    assert by_title["Software Engineer"].raw == {"source": "weworkremotely"}
    assert by_title["Platform Engineer"].external_id == _JOB_B
    assert by_title["Platform Engineer"].location == "Worldwide"
    assert by_title["Implementation Engineer"].external_id == _JOB_C
    assert by_title["Implementation Engineer"].location == "Europe"
    assert by_title["Data Engineer"].external_id == _JOB_D
    assert by_title["Product Manager"].external_id == _JOB_E


def test_weworkremotely_parser_ignores_non_posting_links() -> None:
    """Only WeWorkRemotely detail links should become candidates."""

    adapter = WeworkremotelyAdapter(user_agent="test-agent")
    nav_only_html = f"""
    <a href="/remote-jobs">Index</a>
    <a href="/jobs">Index</a>
    <a href="/job">Index</a>
    <a href="/listings">Index</a>
    <a href="/listing">Index</a>
    <a href="{_PATH_A}/apply">Apply</a>
    <a href="/jobs/{_JOB_A}/login">Login</a>
    <a href="/about">About</a>
    <a href="/index">Index</a>
    <a href="/login">Login home</a>
    """
    jobs = adapter._parse_html(
        "https://weworkremotely.com/",
        nav_only_html,
        max_jobs=10,
    )

    assert jobs == []


def test_weworkremotely_parser_falls_back_to_title_attribute() -> None:
    """Empty anchor text should fall back to title attributes."""

    adapter = WeworkremotelyAdapter(user_agent="test-agent")
    html = f"""
    <a href="{_PATH_A}" title="Attr Title" data-location="Remote"></a>
    <a href="{_PATH_B}" aria-label="Aria Title" data-location="Berlin"></a>
    """
    jobs = adapter._parse_html(
        "https://weworkremotely.com/",
        html,
        max_jobs=10,
    )

    by_title = {job.title: job for job in jobs}
    assert by_title["Attr Title"].external_id == _JOB_A
    assert by_title["Attr Title"].location == "Remote"
    assert by_title["Aria Title"].external_id == _JOB_B
    assert by_title["Aria Title"].location == "Berlin"


def test_weworkremotely_parser_respects_max_jobs() -> None:
    """Parser should stop once max_jobs candidates are collected."""

    adapter = WeworkremotelyAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://weworkremotely.com/",
        WEWORKREMOTELY_SAMPLE_HTML,
        max_jobs=2,
    )

    assert len(jobs) == 2


def test_weworkremotely_parser_returns_empty_for_non_positive_max_jobs() -> None:
    """Non-positive max_jobs should short-circuit to an empty list."""

    adapter = WeworkremotelyAdapter(user_agent="test-agent")
    assert (
        adapter._parse_html("https://weworkremotely.com/", WEWORKREMOTELY_SAMPLE_HTML, max_jobs=0)
        == []
    )
    assert (
        adapter._parse_html("https://weworkremotely.com/", WEWORKREMOTELY_SAMPLE_HTML, max_jobs=-1)
        == []
    )


def test_weworkremotely_parser_uses_remote_flag() -> None:
    """data-remote=true should resolve location to Remote."""

    adapter = WeworkremotelyAdapter(user_agent="test-agent")
    html = f"""
    <a href="{_PATH_A}" data-remote="true">Remote Role</a>
    """
    jobs = adapter._parse_html("https://weworkremotely.com/", html, max_jobs=10)
    assert len(jobs) == 1
    assert jobs[0].location == "Remote"

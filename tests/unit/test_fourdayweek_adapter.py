"""Unit tests for the 4 Day Week careers site adapter."""

from __future__ import annotations

from autoapply_agent.adapters.fourdayweek import FourdayweekAdapter

_A = "48291"
_PATH_A = "/four-day/48291"
_B = "55902"
_PATH_B = "/listings/55902"
_C = "61033"
_PATH_C = "/positions/61033"
_D = "72044"
_PATH_D = "/jobs/72044"
_E = "83055"
_PATH_E = "/job/83055"

FOURDAYWEEK_SAMPLE_HTML = """
<html>
  <body>
    <section class="listings">
      <article class="job">
        <a href="/four-day/48291" class="heading" data-location="Lisbon">
          Software Engineer
        </a>
      </article>
      <article class="job">
        <a href="/listings/55902" class="heading" data-location="Bali">
          Platform Engineer
        </a>
      </article>
      <article class="job">
        <a href="/positions/61033" class="heading" data-job-location="Remote">
          Implementation Engineer
        </a>
      </article>
      <article class="job">
        <a href="/jobs/72044" class="heading" data-location="Berlin">
          Data Engineer
        </a>
      </article>
      <article class="job">
        <a href="/job/83055" class="heading" data-location="Tokyo">
          Product Manager
        </a>
      </article>
    </section>
    <a href="/four-day">Index</a>
    <a href="/listings">Index</a>
    <a href="/positions">Index</a>
    <a href="/jobs">Index</a>
    <a href="/job">Index</a>
    <a href="/four-day/48291/apply">Apply</a>
    <a href="/about">About</a>
    <a href="/index">Index page</a>
  </body>
</html>
"""


def test_fourdayweek_parser_extracts_jobs() -> None:
    """4 Day Week parser should extract posting fields and skip nav/apply links."""

    adapter = FourdayweekAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://4dayweek.io/jobs",
        FOURDAYWEEK_SAMPLE_HTML,
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
    assert by_title["Software Engineer"].external_id == _A
    assert by_title["Software Engineer"].location == "Lisbon"
    assert by_title["Software Engineer"].url.endswith(_PATH_A)
    assert by_title["Software Engineer"].raw == {"source": "fourdayweek"}
    assert by_title["Platform Engineer"].external_id == _B
    assert by_title["Platform Engineer"].location == "Bali"
    assert by_title["Implementation Engineer"].external_id == _C
    assert by_title["Implementation Engineer"].location == "Remote"
    assert by_title["Implementation Engineer"].url.endswith(_PATH_C)
    assert by_title["Data Engineer"].external_id == _D
    assert by_title["Product Manager"].external_id == _E


def test_fourdayweek_parser_ignores_non_posting_links() -> None:
    """Only 4 Day Week detail links should become candidates."""

    adapter = FourdayweekAdapter(user_agent="test-agent")
    nav_only_html = f"""
    <a href="/four-day">Index</a>
    <a href="/listings">Index</a>
    <a href="/positions">Index</a>
    <a href="/jobs">Index</a>
    <a href="/job">Index</a>
    <a href="{_PATH_A}/apply">Apply</a>
    <a href="/four-day/{_A}/login">Login</a>
    <a href="/positions/{_C}/apply">Apply role</a>
    <a href="/about">About</a>
    <a href="/index">Index</a>
    <a href="/login">Login home</a>
    """
    jobs = adapter._parse_html(
        "https://4dayweek.io/jobs",
        nav_only_html,
        max_jobs=10,
    )

    assert jobs == []


def test_fourdayweek_parser_falls_back_to_title_attribute() -> None:
    """Empty anchor text should fall back to title attributes."""

    adapter = FourdayweekAdapter(user_agent="test-agent")
    html = f"""
    <a href="{_PATH_A}" title="Attr Title" data-location="Remote"></a>
    <a href="{_PATH_B}" aria-label="Aria Title" data-location="Lisbon"></a>
    """
    jobs = adapter._parse_html(
        "https://4dayweek.io/jobs",
        html,
        max_jobs=10,
    )

    by_title = {job.title: job for job in jobs}
    assert by_title["Attr Title"].external_id == _A
    assert by_title["Attr Title"].location == "Remote"
    assert by_title["Aria Title"].external_id == _B
    assert by_title["Aria Title"].location == "Lisbon"


def test_fourdayweek_parser_respects_max_jobs() -> None:
    """Parser should stop once max_jobs candidates are collected."""

    adapter = FourdayweekAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://4dayweek.io/jobs",
        FOURDAYWEEK_SAMPLE_HTML,
        max_jobs=2,
    )

    assert len(jobs) == 2


def test_fourdayweek_parser_returns_empty_for_non_positive_max_jobs() -> None:
    """Non-positive max_jobs should short-circuit to an empty list."""

    adapter = FourdayweekAdapter(user_agent="test-agent")
    assert (
        adapter._parse_html("https://4dayweek.io/jobs", FOURDAYWEEK_SAMPLE_HTML, max_jobs=0) == []
    )
    assert (
        adapter._parse_html("https://4dayweek.io/jobs", FOURDAYWEEK_SAMPLE_HTML, max_jobs=-1) == []
    )


def test_fourdayweek_parser_uses_remote_flag() -> None:
    """data-remote=true should resolve location to Remote."""

    adapter = FourdayweekAdapter(user_agent="test-agent")
    html = f"""
    <a href="{_PATH_A}" data-remote="true">Remote Role</a>
    """
    jobs = adapter._parse_html("https://4dayweek.io/jobs", html, max_jobs=10)
    assert len(jobs) == 1
    assert jobs[0].location == "Remote"

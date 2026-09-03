"""Unit tests for the Glassdoor careers site adapter."""

from __future__ import annotations

from autoapply_agent.adapters.glassdoor import GlassdoorAdapter

_A = "49102"
_A_PATH = "/reviews/49102"
_B = "56213"
_B_PATH = "/jobs/56213"
_C = "62324"
_C_PATH = "/job-listing/62324"
_D = "73435"
_D_PATH = "/positions/73435"
_E = "84546"
_E_PATH = "/openings/84546"

GLASSDOOR_SAMPLE_HTML = """
<html>
  <body>
    <section class="listings">
      <article class="job">
        <a href="/reviews/49102" class="heading" data-location="Lisbon">
          Software Engineer
        </a>
      </article>
      <article class="job">
        <a href="/jobs/56213" class="heading" data-location="Bali">
          Platform Engineer
        </a>
      </article>
      <article class="job">
        <a href="/job-listing/62324" class="heading" data-job-location="Remote">
          Implementation Engineer
        </a>
      </article>
      <article class="job">
        <a href="/positions/73435" class="heading" data-location="Berlin">
          Data Engineer
        </a>
      </article>
      <article class="job">
        <a href="/openings/84546" class="heading" data-location="Tokyo">
          Product Manager
        </a>
      </article>
    </section>
    <a href="/reviews">Index</a>
    <a href="/jobs">Index</a>
    <a href="/job-listing">Index</a>
    <a href="/positions">Index</a>
    <a href="/openings">Index</a>
    <a href="/reviews/49102/apply">Apply</a>
    <a href="/about">About</a>
    <a href="/index">Index page</a>
  </body>
</html>
"""


def test_glassdoor_parser_extracts_jobs() -> None:
    """Glassdoor parser should extract posting fields and skip nav/apply links."""

    adapter = GlassdoorAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://www.glassdoor.com/jobs",
        GLASSDOOR_SAMPLE_HTML,
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
    assert by_title["Software Engineer"].url.endswith(_A_PATH)
    assert by_title["Software Engineer"].raw == {"source": "glassdoor"}
    assert by_title["Platform Engineer"].external_id == _B
    assert by_title["Platform Engineer"].location == "Bali"
    assert by_title["Implementation Engineer"].external_id == _C
    assert by_title["Implementation Engineer"].location == "Remote"
    assert by_title["Implementation Engineer"].url.endswith(_C_PATH)
    assert by_title["Data Engineer"].external_id == _D
    assert by_title["Product Manager"].external_id == _E


def test_glassdoor_parser_ignores_non_posting_links() -> None:
    """Only Glassdoor detail links should become candidates."""

    adapter = GlassdoorAdapter(user_agent="test-agent")
    nav_only_html = f"""
    <a href="/reviews">Index</a>
    <a href="/jobs">Index</a>
    <a href="/job-listing">Index</a>
    <a href="/positions">Index</a>
    <a href="/openings">Index</a>
    <a href="{_A_PATH}/apply">Apply</a>
    <a href="/reviews/{_A}/login">Login</a>
    <a href="/positions/{_D}/apply">Apply role</a>
    <a href="/about">About</a>
    <a href="/index">Index</a>
    <a href="/login">Login home</a>
    """
    jobs = adapter._parse_html(
        "https://www.glassdoor.com/jobs",
        nav_only_html,
        max_jobs=10,
    )

    assert jobs == []


def test_glassdoor_parser_falls_back_to_title_attribute() -> None:
    """Empty anchor text should fall back to title attributes."""

    adapter = GlassdoorAdapter(user_agent="test-agent")
    html = f"""
    <a href="{_A_PATH}" title="Attr Title" data-location="Remote"></a>
    <a href="{_B_PATH}" aria-label="Aria Title" data-location="Lisbon"></a>
    """
    jobs = adapter._parse_html(
        "https://www.glassdoor.com/jobs",
        html,
        max_jobs=10,
    )

    by_title = {job.title: job for job in jobs}
    assert by_title["Attr Title"].external_id == _A
    assert by_title["Attr Title"].location == "Remote"
    assert by_title["Aria Title"].external_id == _B
    assert by_title["Aria Title"].location == "Lisbon"


def test_glassdoor_parser_respects_max_jobs() -> None:
    """Parser should stop once max_jobs candidates are collected."""

    adapter = GlassdoorAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://www.glassdoor.com/jobs",
        GLASSDOOR_SAMPLE_HTML,
        max_jobs=2,
    )

    assert len(jobs) == 2


def test_glassdoor_parser_returns_empty_for_non_positive_max_jobs() -> None:
    """Non-positive max_jobs should short-circuit to an empty list."""

    adapter = GlassdoorAdapter(user_agent="test-agent")
    assert (
        adapter._parse_html("https://www.glassdoor.com/jobs", GLASSDOOR_SAMPLE_HTML, max_jobs=0)
        == []
    )
    assert (
        adapter._parse_html("https://www.glassdoor.com/jobs", GLASSDOOR_SAMPLE_HTML, max_jobs=-1)
        == []
    )


def test_glassdoor_parser_uses_remote_flag() -> None:
    """data-remote=true should resolve location to Remote."""

    adapter = GlassdoorAdapter(user_agent="test-agent")
    html = f"""
    <a href="{_A_PATH}" data-remote="true">Remote Role</a>
    """
    jobs = adapter._parse_html("https://www.glassdoor.com/jobs", html, max_jobs=10)
    assert len(jobs) == 1
    assert jobs[0].location == "Remote"

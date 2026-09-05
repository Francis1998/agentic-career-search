"""Unit tests for the Naukri careers site adapter."""

from __future__ import annotations

from autoapply_agent.adapters.naukri import NaukriAdapter

_A = "49102"
_A_PATH = "/job-listings/49102"
_B = "56213"
_B_PATH = "/jobdetail/56213"
_C = "62324"
_C_PATH = "/jobs/62324"
_D = "73435"
_D_PATH = "/job-description/73435"
_E = "84546"
_E_PATH = "/recruiters/job/84546"

NAUKRI_SAMPLE_HTML = """
<html>
  <body>
    <section class="listings">
      <article class="job">
        <a href="/job-listings/49102" class="heading" data-location="Bengaluru">
          Software Engineer
        </a>
      </article>
      <article class="job">
        <a href="/jobdetail/56213" class="heading" data-location="Hyderabad">
          Platform Engineer
        </a>
      </article>
      <article class="job">
        <a href="/jobs/62324" class="heading" data-job-location="Remote">
          Implementation Engineer
        </a>
      </article>
      <article class="job">
        <a href="/job-description/73435" class="heading" data-location="Pune">
          Data Engineer
        </a>
      </article>
      <article class="job">
        <a href="/recruiters/job/84546" class="heading" data-location="Mumbai">
          Product Manager
        </a>
      </article>
    </section>
    <a href="/job-listings">Index</a>
    <a href="/jobdetail">Index</a>
    <a href="/jobs">Index</a>
    <a href="/job-description">Index</a>
    <a href="/recruiters/job">Index</a>
    <a href="/jobs/49102/apply">Apply</a>
    <a href="/about">About</a>
    <a href="/index">Index page</a>
  </body>
</html>
"""


def test_naukri_parser_extracts_jobs() -> None:
    """Naukri parser should extract posting fields and skip nav/apply links."""

    adapter = NaukriAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://www.naukri.com/jobs",
        NAUKRI_SAMPLE_HTML,
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
    assert by_title["Software Engineer"].location == "Bengaluru"
    assert by_title["Software Engineer"].url.endswith(_A_PATH)
    assert by_title["Software Engineer"].raw == {"source": "naukri"}
    assert by_title["Platform Engineer"].external_id == _B
    assert by_title["Platform Engineer"].location == "Hyderabad"
    assert by_title["Implementation Engineer"].external_id == _C
    assert by_title["Implementation Engineer"].location == "Remote"
    assert by_title["Implementation Engineer"].url.endswith(_C_PATH)
    assert by_title["Data Engineer"].external_id == _D
    assert by_title["Data Engineer"].url.endswith(_D_PATH)
    assert by_title["Product Manager"].external_id == _E
    assert by_title["Product Manager"].url.endswith(_E_PATH)


def test_naukri_parser_ignores_non_posting_links() -> None:
    """Only Naukri detail links should become candidates."""

    adapter = NaukriAdapter(user_agent="test-agent")
    nav_only_html = f"""
    <a href="/job-listings">Index</a>
    <a href="/jobdetail">Index</a>
    <a href="/jobs">Index</a>
    <a href="/job-description">Index</a>
    <a href="/recruiters/job">Index</a>
    <a href="{_A_PATH}/apply">Apply</a>
    <a href="/job-listings/{_A}/login">Login</a>
    <a href="{_D_PATH}/apply">Apply role</a>
    <a href="/about">About</a>
    <a href="/index">Index</a>
    <a href="/login">Login home</a>
    """
    jobs = adapter._parse_html(
        "https://www.naukri.com/jobs",
        nav_only_html,
        max_jobs=10,
    )

    assert jobs == []


def test_naukri_parser_falls_back_to_title_attribute() -> None:
    """Empty anchor text should fall back to title attributes."""

    adapter = NaukriAdapter(user_agent="test-agent")
    html = f"""
    <a href="{_A_PATH}" title="Attr Title" data-location="Remote"></a>
    <a href="{_B_PATH}" aria-label="Aria Title" data-location="Bengaluru"></a>
    """
    jobs = adapter._parse_html(
        "https://www.naukri.com/jobs",
        html,
        max_jobs=10,
    )

    by_title = {job.title: job for job in jobs}
    assert by_title["Attr Title"].external_id == _A
    assert by_title["Attr Title"].location == "Remote"
    assert by_title["Aria Title"].external_id == _B
    assert by_title["Aria Title"].location == "Bengaluru"


def test_naukri_parser_respects_max_jobs() -> None:
    """Parser should stop once max_jobs candidates are collected."""

    adapter = NaukriAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://www.naukri.com/jobs",
        NAUKRI_SAMPLE_HTML,
        max_jobs=2,
    )

    assert len(jobs) == 2


def test_naukri_parser_returns_empty_for_non_positive_max_jobs() -> None:
    """Non-positive max_jobs should short-circuit to an empty list."""

    adapter = NaukriAdapter(user_agent="test-agent")
    assert (
        adapter._parse_html(
            "https://www.naukri.com/jobs",
            NAUKRI_SAMPLE_HTML,
            max_jobs=0,
        )
        == []
    )
    assert (
        adapter._parse_html(
            "https://www.naukri.com/jobs",
            NAUKRI_SAMPLE_HTML,
            max_jobs=-1,
        )
        == []
    )


def test_naukri_parser_uses_remote_flag() -> None:
    """data-remote=true should resolve location to Remote."""

    adapter = NaukriAdapter(user_agent="test-agent")
    html = f"""
    <a href="{_A_PATH}" data-remote="true">Remote Role</a>
    """
    jobs = adapter._parse_html("https://www.naukri.com/jobs", html, max_jobs=10)
    assert len(jobs) == 1
    assert jobs[0].location == "Remote"

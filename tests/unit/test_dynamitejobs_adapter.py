"""Unit tests for the Dynamitejobs careers site adapter."""

from __future__ import annotations

from autoapply_agent.adapters.dynamitejobs import DynamitejobsAdapter

_JOB_A = "48291"
_PATH_A = "/jobs/48291"
_JOB_B = "55902"
_PATH_B = "/job/55902"
_JOB_C = "61033"
_PATH_C = "/remote-jobs/61033"
_JOB_D = "72044"
_PATH_D = "/positions/72044"
_JOB_E = "83055"
_PATH_E = "/listings/83055"

DYNAMITEJOBS_SAMPLE_HTML = """
<html>
  <body>
    <section class="listings">
      <article class="job">
        <a href="/jobs/48291" class="heading" data-location="Lisbon">
          Software Engineer
        </a>
      </article>
      <article class="job">
        <a href="/job/55902" class="heading" data-location="Bali">
          Platform Engineer
        </a>
      </article>
      <article class="job">
        <a href="/remote-jobs/61033" class="heading" data-job-location="Remote">
          Implementation Engineer
        </a>
      </article>
      <article class="job">
        <a href="/positions/72044" class="heading" data-location="Berlin">
          Data Engineer
        </a>
      </article>
      <article class="job">
        <a href="/listings/83055" class="heading" data-location="Tokyo">
          Product Manager
        </a>
      </article>
    </section>
    <a href="/jobs">Index</a>
    <a href="/job">Index</a>
    <a href="/remote-jobs">Index</a>
    <a href="/positions">Index</a>
    <a href="/listings">Index</a>
    <a href="/jobs/48291/apply">Apply</a>
    <a href="/about">About</a>
    <a href="/index">Index page</a>
  </body>
</html>
"""


def test_dynamitejobs_parser_extracts_jobs() -> None:
    """Dynamitejobs parser should extract posting fields and skip nav/apply links."""

    adapter = DynamitejobsAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://dynamitejobs.com/remote-jobs",
        DYNAMITEJOBS_SAMPLE_HTML,
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
    assert by_title["Software Engineer"].location == "Lisbon"
    assert by_title["Software Engineer"].url.endswith(_PATH_A)
    assert by_title["Software Engineer"].raw == {"source": "dynamitejobs"}
    assert by_title["Platform Engineer"].external_id == _JOB_B
    assert by_title["Platform Engineer"].location == "Bali"
    assert by_title["Implementation Engineer"].external_id == _JOB_C
    assert by_title["Implementation Engineer"].location == "Remote"
    assert by_title["Implementation Engineer"].url.endswith(_PATH_C)
    assert by_title["Data Engineer"].external_id == _JOB_D
    assert by_title["Product Manager"].external_id == _JOB_E


def test_dynamitejobs_parser_ignores_non_posting_links() -> None:
    """Only Dynamitejobs detail links should become candidates."""

    adapter = DynamitejobsAdapter(user_agent="test-agent")
    nav_only_html = f"""
    <a href="/jobs">Index</a>
    <a href="/job">Index</a>
    <a href="/remote-jobs">Index</a>
    <a href="/positions">Index</a>
    <a href="/listings">Index</a>
    <a href="{_PATH_A}/apply">Apply</a>
    <a href="/jobs/{_JOB_A}/login">Login</a>
    <a href="/remote-jobs/{_JOB_C}/apply">Apply remote</a>
    <a href="/about">About</a>
    <a href="/index">Index</a>
    <a href="/login">Login home</a>
    """
    jobs = adapter._parse_html(
        "https://dynamitejobs.com/remote-jobs",
        nav_only_html,
        max_jobs=10,
    )

    assert jobs == []


def test_dynamitejobs_parser_falls_back_to_title_attribute() -> None:
    """Empty anchor text should fall back to title attributes."""

    adapter = DynamitejobsAdapter(user_agent="test-agent")
    html = f"""
    <a href="{_PATH_A}" title="Attr Title" data-location="Remote"></a>
    <a href="{_PATH_B}" aria-label="Aria Title" data-location="Lisbon"></a>
    """
    jobs = adapter._parse_html(
        "https://dynamitejobs.com/remote-jobs",
        html,
        max_jobs=10,
    )

    by_title = {job.title: job for job in jobs}
    assert by_title["Attr Title"].external_id == _JOB_A
    assert by_title["Attr Title"].location == "Remote"
    assert by_title["Aria Title"].external_id == _JOB_B
    assert by_title["Aria Title"].location == "Lisbon"


def test_dynamitejobs_parser_respects_max_jobs() -> None:
    """Parser should stop once max_jobs candidates are collected."""

    adapter = DynamitejobsAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://dynamitejobs.com/remote-jobs",
        DYNAMITEJOBS_SAMPLE_HTML,
        max_jobs=2,
    )

    assert len(jobs) == 2


def test_dynamitejobs_parser_returns_empty_for_non_positive_max_jobs() -> None:
    """Non-positive max_jobs should short-circuit to an empty list."""

    adapter = DynamitejobsAdapter(user_agent="test-agent")
    assert (
        adapter._parse_html("https://dynamitejobs.com/remote-jobs", DYNAMITEJOBS_SAMPLE_HTML, max_jobs=0)
        == []
    )
    assert (
        adapter._parse_html(
            "https://dynamitejobs.com/remote-jobs", DYNAMITEJOBS_SAMPLE_HTML, max_jobs=-1
        )
        == []
    )


def test_dynamitejobs_parser_uses_remote_flag() -> None:
    """data-remote=true should resolve location to Remote."""

    adapter = DynamitejobsAdapter(user_agent="test-agent")
    html = f"""
    <a href="{_PATH_A}" data-remote="true">Remote Role</a>
    """
    jobs = adapter._parse_html("https://dynamitejobs.com/remote-jobs", html, max_jobs=10)
    assert len(jobs) == 1
    assert jobs[0].location == "Remote"

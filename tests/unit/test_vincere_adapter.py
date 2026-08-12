"""Unit tests for the Vincere careers site adapter."""

from __future__ import annotations

from autoapply_agent.adapters.vincere import VincereAdapter

_JOB_A = "48291"
_JOB_B = "55902"
_JOB_C = "61033"
_JOB_D = "72044"
_JOB_E = "83055"
_PATH_A = f"/jobs/{_JOB_A}"
_PATH_B = f"/job/{_JOB_B}"
_PATH_C = f"/careers/{_JOB_C}"
_PATH_D = f"/careers/job/{_JOB_D}"
_PATH_E = f"/job-detail/{_JOB_E}"

VINCERE_SAMPLE_HTML = f"""
<html>
  <body>
    <section class="listings">
      <article class="job">
        <a href="{_PATH_A}"
           class="heading"
           data-location="Remote">
          Software Engineer
        </a>
      </article>
      <article class="job">
        <a href="{_PATH_B}"
           class="heading"
           data-location="San Francisco">
          Platform Engineer
        </a>
      </article>
      <article class="job">
        <a href="{_PATH_C}"
           class="heading"
           data-job-location="New York">
          Implementation Engineer
        </a>
      </article>
      <article class="job">
        <a href="{_PATH_D}"
           class="heading"
           data-location="Austin">
          Data Engineer
        </a>
      </article>
      <article class="job">
        <a href="{_PATH_E}"
           class="heading"
           data-location="London">
          Product Manager
        </a>
      </article>
    </section>
    <a href="/jobs">All jobs</a>
    <a href="/careers">Careers index</a>
    <a href="/job-detail">Index</a>
    <a href="{_PATH_A}/apply">Apply</a>
    <a href="/about">About</a>
  </body>
</html>
"""


def test_vincere_parser_extracts_jobs() -> None:
    """Vincere parser should extract posting fields and skip nav/apply links."""

    adapter = VincereAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://acme.vincere.io/jobs/",
        VINCERE_SAMPLE_HTML,
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
    assert by_title["Software Engineer"].raw == {"source": "vincere"}
    assert by_title["Platform Engineer"].external_id == _JOB_B
    assert by_title["Platform Engineer"].location == "San Francisco"
    assert by_title["Implementation Engineer"].external_id == _JOB_C
    assert by_title["Implementation Engineer"].location == "New York"
    assert by_title["Data Engineer"].external_id == _JOB_D
    assert by_title["Product Manager"].external_id == _JOB_E


def test_vincere_parser_ignores_non_posting_links() -> None:
    """Only Vincere detail links should become candidates."""

    adapter = VincereAdapter(user_agent="test-agent")
    nav_only_html = f"""
    <a href="/jobs">All jobs</a>
    <a href="/careers">Careers index</a>
    <a href="/job-detail">Index</a>
    <a href="{_PATH_A}/apply">Apply</a>
    <a href="/jobs/{_JOB_A}/login">Login</a>
    <a href="/about">About</a>
    <a href="/login">Login home</a>
    """
    jobs = adapter._parse_html(
        "https://acme.vincere.io/jobs/",
        nav_only_html,
        max_jobs=10,
    )

    assert jobs == []


def test_vincere_parser_falls_back_to_title_attribute() -> None:
    """Empty anchor text should fall back to title attributes."""

    adapter = VincereAdapter(user_agent="test-agent")
    html = f"""
    <a href="{_PATH_A}" title="Attr Title" data-location="Remote"></a>
    <a href="{_PATH_B}" aria-label="Aria Title" data-location="Berlin"></a>
    """
    jobs = adapter._parse_html(
        "https://acme.vincere.io/jobs/",
        html,
        max_jobs=10,
    )

    by_title = {job.title: job for job in jobs}
    assert set(by_title) == {"Attr Title", "Aria Title"}


def test_vincere_parser_respects_max_jobs() -> None:
    """Parsing should stop at max_jobs."""

    adapter = VincereAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://acme.vincere.io/jobs/",
        VINCERE_SAMPLE_HTML,
        max_jobs=2,
    )

    assert len(jobs) == 2


def test_vincere_parser_returns_empty_for_non_positive_max_jobs() -> None:
    """Non-positive max_jobs should short-circuit."""

    adapter = VincereAdapter(user_agent="test-agent")
    assert (
        adapter._parse_html(
            "https://acme.vincere.io/jobs/",
            VINCERE_SAMPLE_HTML,
            max_jobs=0,
        )
        == []
    )

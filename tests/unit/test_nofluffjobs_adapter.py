"""Unit tests for the No Fluff Jobs careers site adapter."""

from __future__ import annotations

from autoapply_agent.adapters.nofluffjobs import NofluffjobsAdapter

_A = "70113"
_PATH_A = "/pl/70113"
_B = "77224"
_PATH_B = "/job/77224"
_C = "83335"
_PATH_C = "/offers/83335"
_D = "94446"
_PATH_D = "/positions/94446"
_E = "105557"
_PATH_E = "/jobs/105557"

Nofluffjobs_SAMPLE_HTML = """
<html>
  <body>
    <section class="listings">
      <article class="job">
        <a href="/pl/70113" class="heading" data-location="Warsaw">
          Backend Engineer
        </a>
      </article>
      <article class="job">
        <a href="/job/77224" class="heading" data-location="Krakow">
          Frontend Engineer
        </a>
      </article>
      <article class="job">
        <a href="/offers/83335" class="heading" data-job-location="Remote">
          DevOps Engineer
        </a>
      </article>
      <article class="job">
        <a href="/positions/94446" class="heading" data-location="Berlin">
          Data Engineer
        </a>
      </article>
      <article class="job">
        <a href="/jobs/105557" class="heading" data-location="Prague">
          Product Manager
        </a>
      </article>
    </section>
    <a href="/pl">Index</a>
    <a href="/job">Index</a>
    <a href="/offers">Index</a>
    <a href="/positions">Index</a>
    <a href="/jobs">Index</a>
    <a href="/pl/70113/apply">Apply</a>
    <a href="/about">About</a>
    <a href="/index">Index page</a>
  </body>
</html>
"""


def test_nofluffjobs_parser_extracts_jobs() -> None:
    """No Fluff Jobs parser should extract posting fields and skip nav/apply links."""

    adapter = NofluffjobsAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://nofluffjobs.com/jobs",
        Nofluffjobs_SAMPLE_HTML,
        max_jobs=10,
    )

    by_title = {job.title: job for job in jobs}
    assert set(by_title) == {
        "Backend Engineer",
        "Frontend Engineer",
        "DevOps Engineer",
        "Data Engineer",
        "Product Manager",
    }
    assert by_title["Backend Engineer"].external_id == _A
    assert by_title["Backend Engineer"].location == "Warsaw"
    assert by_title["Backend Engineer"].url.endswith(_PATH_A)
    assert by_title["Backend Engineer"].raw == {"source": "nofluffjobs"}
    assert by_title["Frontend Engineer"].external_id == _B
    assert by_title["Frontend Engineer"].location == "Krakow"
    assert by_title["DevOps Engineer"].external_id == _C
    assert by_title["DevOps Engineer"].location == "Remote"
    assert by_title["DevOps Engineer"].url.endswith(_PATH_C)
    assert by_title["Data Engineer"].external_id == _D
    assert by_title["Product Manager"].external_id == _E


def test_nofluffjobs_parser_ignores_non_posting_links() -> None:
    """Only No Fluff Jobs detail links should become candidates."""

    adapter = NofluffjobsAdapter(user_agent="test-agent")
    nav_only_html = f"""
    <a href="/pl">Index</a>
    <a href="/job">Index</a>
    <a href="/offers">Index</a>
    <a href="/positions">Index</a>
    <a href="/jobs">Index</a>
    <a href="{_PATH_A}/apply">Apply</a>
    <a href="/pl/{_A}/login">Login</a>
    <a href="/offers/{_C}/apply">Apply role</a>
    <a href="/about">About</a>
    <a href="/index">Index</a>
    <a href="/login">Login home</a>
    """
    jobs = adapter._parse_html(
        "https://nofluffjobs.com/jobs",
        nav_only_html,
        max_jobs=10,
    )

    assert jobs == []


def test_nofluffjobs_parser_falls_back_to_title_attribute() -> None:
    """Empty anchor text should fall back to title attributes."""

    adapter = NofluffjobsAdapter(user_agent="test-agent")
    html = f"""
    <a href="{_PATH_A}" title="Attr Title" data-location="Remote"></a>
    <a href="{_PATH_B}" aria-label="Aria Title" data-location="Lisbon"></a>
    """
    jobs = adapter._parse_html(
        "https://nofluffjobs.com/jobs",
        html,
        max_jobs=10,
    )

    by_title = {job.title: job for job in jobs}
    assert by_title["Attr Title"].external_id == _A
    assert by_title["Attr Title"].location == "Remote"
    assert by_title["Aria Title"].external_id == _B
    assert by_title["Aria Title"].location == "Lisbon"


def test_nofluffjobs_parser_respects_max_jobs() -> None:
    """Parser should stop once max_jobs candidates are collected."""

    adapter = NofluffjobsAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://nofluffjobs.com/jobs",
        Nofluffjobs_SAMPLE_HTML,
        max_jobs=2,
    )

    assert len(jobs) == 2


def test_nofluffjobs_parser_returns_empty_for_non_positive_max_jobs() -> None:
    """Non-positive max_jobs should short-circuit to an empty list."""

    adapter = NofluffjobsAdapter(user_agent="test-agent")
    assert (
        adapter._parse_html(
            "https://nofluffjobs.com/jobs",
            Nofluffjobs_SAMPLE_HTML,
            max_jobs=0,
        )
        == []
    )
    assert (
        adapter._parse_html(
            "https://nofluffjobs.com/jobs",
            Nofluffjobs_SAMPLE_HTML,
            max_jobs=-1,
        )
        == []
    )


def test_nofluffjobs_parser_uses_remote_flag() -> None:
    """data-remote=true should resolve location to Remote."""

    adapter = NofluffjobsAdapter(user_agent="test-agent")
    html = f"""
    <a href="{_PATH_A}" data-remote="true">Remote Role</a>
    """
    jobs = adapter._parse_html("https://nofluffjobs.com/jobs", html, max_jobs=10)
    assert len(jobs) == 1
    assert jobs[0].location == "Remote"

"""Unit tests for the Totaljobs careers site adapter."""

from __future__ import annotations

from autoapply_agent.adapters.totaljobs import TotaljobsAdapter

_A = "49102"
_A_PATH = "/job/49102"
_B = "56213"
_B_PATH = "/jobs/56213"
_C = "62324"
_C_PATH = "/job-vacancy/62324"
_D = "73435"
_D_PATH = "/details/73435"
_E = "84546"
_E_PATH = "/uk/job/84546"

TOTALJOBS_SAMPLE_HTML = """
<html>
  <body>
    <section class="listings">
      <article class="job">
        <a href="/job/49102" class="heading" data-location="London">
          Software Engineer
        </a>
      </article>
      <article class="job">
        <a href="/jobs/56213" class="heading" data-location="Manchester">
          Platform Engineer
        </a>
      </article>
      <article class="job">
        <a href="/job-vacancy/62324" class="heading" data-job-location="Remote">
          Implementation Engineer
        </a>
      </article>
      <article class="job">
        <a href="/details/73435" class="heading" data-location="Birmingham">
          Data Engineer
        </a>
      </article>
      <article class="job">
        <a href="/uk/job/84546" class="heading" data-location="Leeds">
          Product Manager
        </a>
      </article>
    </section>
    <a href="/job">Index</a>
    <a href="/jobs">Index</a>
    <a href="/job-vacancy">Index</a>
    <a href="/details">Index</a>
    <a href="/uk/job">Index</a>
    <a href="/jobs/49102/apply">Apply</a>
    <a href="/about">About</a>
    <a href="/index">Index page</a>
  </body>
</html>
"""


def test_totaljobs_parser_extracts_jobs() -> None:
    """Totaljobs parser should extract posting fields and skip nav/apply links."""

    adapter = TotaljobsAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://www.totaljobs.com/jobs",
        TOTALJOBS_SAMPLE_HTML,
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
    assert by_title["Software Engineer"].location == "London"
    assert by_title["Software Engineer"].url.endswith(_A_PATH)
    assert by_title["Software Engineer"].raw == {"source": "totaljobs"}
    assert by_title["Platform Engineer"].external_id == _B
    assert by_title["Platform Engineer"].location == "Manchester"
    assert by_title["Implementation Engineer"].external_id == _C
    assert by_title["Implementation Engineer"].location == "Remote"
    assert by_title["Implementation Engineer"].url.endswith(_C_PATH)
    assert by_title["Data Engineer"].external_id == _D
    assert by_title["Data Engineer"].url.endswith(_D_PATH)
    assert by_title["Product Manager"].external_id == _E
    assert by_title["Product Manager"].url.endswith(_E_PATH)


def test_totaljobs_parser_ignores_non_posting_links() -> None:
    """Only Totaljobs detail links should become candidates."""

    adapter = TotaljobsAdapter(user_agent="test-agent")
    nav_only_html = f"""
    <a href="/job">Index</a>
    <a href="/jobs">Index</a>
    <a href="/job-vacancy">Index</a>
    <a href="/details">Index</a>
    <a href="/uk/job">Index</a>
    <a href="{_A_PATH}/apply">Apply</a>
    <a href="/job/{_A}/login">Login</a>
    <a href="{_D_PATH}/apply">Apply role</a>
    <a href="/about">About</a>
    <a href="/index">Index</a>
    <a href="/login">Login home</a>
    """
    jobs = adapter._parse_html(
        "https://www.totaljobs.com/jobs",
        nav_only_html,
        max_jobs=10,
    )

    assert jobs == []


def test_totaljobs_parser_falls_back_to_title_attribute() -> None:
    """Empty anchor text should fall back to title attributes."""

    adapter = TotaljobsAdapter(user_agent="test-agent")
    html = f"""
    <a href="{_A_PATH}" title="Attr Title" data-location="Remote"></a>
    <a href="{_B_PATH}" aria-label="Aria Title" data-location="London"></a>
    """
    jobs = adapter._parse_html(
        "https://www.totaljobs.com/jobs",
        html,
        max_jobs=10,
    )

    by_title = {job.title: job for job in jobs}
    assert by_title["Attr Title"].external_id == _A
    assert by_title["Attr Title"].location == "Remote"
    assert by_title["Aria Title"].external_id == _B
    assert by_title["Aria Title"].location == "London"


def test_totaljobs_parser_respects_max_jobs() -> None:
    """Parser should stop once max_jobs candidates are collected."""

    adapter = TotaljobsAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://www.totaljobs.com/jobs",
        TOTALJOBS_SAMPLE_HTML,
        max_jobs=2,
    )

    assert len(jobs) == 2


def test_totaljobs_parser_returns_empty_for_non_positive_max_jobs() -> None:
    """Non-positive max_jobs should short-circuit to an empty list."""

    adapter = TotaljobsAdapter(user_agent="test-agent")
    assert (
        adapter._parse_html(
            "https://www.totaljobs.com/jobs",
            TOTALJOBS_SAMPLE_HTML,
            max_jobs=0,
        )
        == []
    )
    assert (
        adapter._parse_html(
            "https://www.totaljobs.com/jobs",
            TOTALJOBS_SAMPLE_HTML,
            max_jobs=-1,
        )
        == []
    )


def test_totaljobs_parser_uses_remote_flag() -> None:
    """data-remote=true should resolve location to Remote."""

    adapter = TotaljobsAdapter(user_agent="test-agent")
    html = f"""
    <a href="{_A_PATH}" data-remote="true">Remote Role</a>
    """
    jobs = adapter._parse_html("https://www.totaljobs.com/jobs", html, max_jobs=10)
    assert len(jobs) == 1
    assert jobs[0].location == "Remote"

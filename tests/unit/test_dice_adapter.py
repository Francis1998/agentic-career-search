"""Unit tests for the Dice careers site adapter."""

from __future__ import annotations

from autoapply_agent.adapters.dice import DiceAdapter

_A = "49102"
_PATH_A = "/positions/49102"
_B = "56213"
_PATH_B = "/jobs/56213"
_C = "62324"
_PATH_C = "/job/62324"
_D = "73435"
_PATH_D = "/listings/73435"
_E = "84546"
_PATH_E = "/tech-jobs/84546"

DICE_SAMPLE_HTML = """
<html>
  <body>
    <section class="listings">
      <article class="job">
        <a href="/positions/49102" class="heading" data-location="Lisbon">
          Software Engineer
        </a>
      </article>
      <article class="job">
        <a href="/jobs/56213" class="heading" data-location="Bali">
          Platform Engineer
        </a>
      </article>
      <article class="job">
        <a href="/job/62324" class="heading" data-job-location="Remote">
          Implementation Engineer
        </a>
      </article>
      <article class="job">
        <a href="/listings/73435" class="heading" data-location="Berlin">
          Data Engineer
        </a>
      </article>
      <article class="job">
        <a href="/tech-jobs/84546" class="heading" data-location="Tokyo">
          Product Manager
        </a>
      </article>
    </section>
    <a href="/positions">Index</a>
    <a href="/jobs">Index</a>
    <a href="/job">Index</a>
    <a href="/listings">Index</a>
    <a href="/tech-jobs">Index</a>
    <a href="/positions/49102/apply">Apply</a>
    <a href="/about">About</a>
    <a href="/index">Index page</a>
  </body>
</html>
"""


def test_dice_parser_extracts_jobs() -> None:
    """Dice parser should extract posting fields and skip nav/apply links."""

    adapter = DiceAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://www.dice.com/jobs",
        DICE_SAMPLE_HTML,
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
    assert by_title["Software Engineer"].raw == {"source": "dice"}
    assert by_title["Platform Engineer"].external_id == _B
    assert by_title["Platform Engineer"].location == "Bali"
    assert by_title["Implementation Engineer"].external_id == _C
    assert by_title["Implementation Engineer"].location == "Remote"
    assert by_title["Implementation Engineer"].url.endswith(_PATH_C)
    assert by_title["Data Engineer"].external_id == _D
    assert by_title["Product Manager"].external_id == _E


def test_dice_parser_ignores_non_posting_links() -> None:
    """Only Dice detail links should become candidates."""

    adapter = DiceAdapter(user_agent="test-agent")
    nav_only_html = f"""
    <a href="/positions">Index</a>
    <a href="/jobs">Index</a>
    <a href="/job">Index</a>
    <a href="/listings">Index</a>
    <a href="/tech-jobs">Index</a>
    <a href="{_PATH_A}/apply">Apply</a>
    <a href="/positions/{_A}/login">Login</a>
    <a href="/job/{_C}/apply">Apply role</a>
    <a href="/about">About</a>
    <a href="/index">Index</a>
    <a href="/login">Login home</a>
    """
    jobs = adapter._parse_html(
        "https://www.dice.com/jobs",
        nav_only_html,
        max_jobs=10,
    )

    assert jobs == []


def test_dice_parser_falls_back_to_title_attribute() -> None:
    """Empty anchor text should fall back to title attributes."""

    adapter = DiceAdapter(user_agent="test-agent")
    html = f"""
    <a href="{_PATH_A}" title="Attr Title" data-location="Remote"></a>
    <a href="{_PATH_B}" aria-label="Aria Title" data-location="Lisbon"></a>
    """
    jobs = adapter._parse_html(
        "https://www.dice.com/jobs",
        html,
        max_jobs=10,
    )

    by_title = {job.title: job for job in jobs}
    assert by_title["Attr Title"].external_id == _A
    assert by_title["Attr Title"].location == "Remote"
    assert by_title["Aria Title"].external_id == _B
    assert by_title["Aria Title"].location == "Lisbon"


def test_dice_parser_respects_max_jobs() -> None:
    """Parser should stop once max_jobs candidates are collected."""

    adapter = DiceAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://www.dice.com/jobs",
        DICE_SAMPLE_HTML,
        max_jobs=2,
    )

    assert len(jobs) == 2


def test_dice_parser_returns_empty_for_non_positive_max_jobs() -> None:
    """Non-positive max_jobs should short-circuit to an empty list."""

    adapter = DiceAdapter(user_agent="test-agent")
    assert adapter._parse_html("https://www.dice.com/jobs", DICE_SAMPLE_HTML, max_jobs=0) == []
    assert adapter._parse_html("https://www.dice.com/jobs", DICE_SAMPLE_HTML, max_jobs=-1) == []


def test_dice_parser_uses_remote_flag() -> None:
    """data-remote=true should resolve location to Remote."""

    adapter = DiceAdapter(user_agent="test-agent")
    html = f"""
    <a href="{_PATH_A}" data-remote="true">Remote Role</a>
    """
    jobs = adapter._parse_html("https://www.dice.com/jobs", html, max_jobs=10)
    assert len(jobs) == 1
    assert jobs[0].location == "Remote"

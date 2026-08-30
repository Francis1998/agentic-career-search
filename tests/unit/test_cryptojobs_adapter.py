"""Unit tests for the Crypto Jobs careers site adapter."""

from __future__ import annotations

from autoapply_agent.adapters.cryptojobs import CryptojobsAdapter

_A = "60113"
_PATH_A = "/crypto-jobs/60113"
_B = "67224"
_PATH_B = "/web3/67224"
_C = "73335"
_PATH_C = "/positions/73335"
_D = "84446"
_PATH_D = "/jobs/84446"
_E = "95557"
_PATH_E = "/job/95557"

Cryptojobs_SAMPLE_HTML = """
<html>
  <body>
    <section class="listings">
      <article class="job">
        <a href="/crypto-jobs/60113" class="heading" data-location="Remote">
          Smart Contract Engineer
        </a>
      </article>
      <article class="job">
        <a href="/web3/67224" class="heading" data-location="Singapore">
          Protocol Engineer
        </a>
      </article>
      <article class="job">
        <a href="/positions/73335" class="heading" data-job-location="Lisbon">
          Security Engineer
        </a>
      </article>
      <article class="job">
        <a href="/jobs/84446" class="heading" data-location="Dubai">
          Data Engineer
        </a>
      </article>
      <article class="job">
        <a href="/job/95557" class="heading" data-location="London">
          Product Manager
        </a>
      </article>
    </section>
    <a href="/crypto-jobs">Index</a>
    <a href="/web3">Index</a>
    <a href="/positions">Index</a>
    <a href="/jobs">Index</a>
    <a href="/job">Index</a>
    <a href="/crypto-jobs/60113/apply">Apply</a>
    <a href="/about">About</a>
    <a href="/index">Index page</a>
  </body>
</html>
"""


def test_cryptojobs_parser_extracts_jobs() -> None:
    """Crypto Jobs parser should extract posting fields and skip nav/apply links."""

    adapter = CryptojobsAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://cryptojobslist.com",
        Cryptojobs_SAMPLE_HTML,
        max_jobs=10,
    )

    by_title = {job.title: job for job in jobs}
    assert set(by_title) == {
        "Smart Contract Engineer",
        "Protocol Engineer",
        "Security Engineer",
        "Data Engineer",
        "Product Manager",
    }
    assert by_title["Smart Contract Engineer"].external_id == _A
    assert by_title["Smart Contract Engineer"].location == "Remote"
    assert by_title["Smart Contract Engineer"].url.endswith(_PATH_A)
    assert by_title["Smart Contract Engineer"].raw == {"source": "cryptojobs"}
    assert by_title["Protocol Engineer"].external_id == _B
    assert by_title["Protocol Engineer"].location == "Singapore"
    assert by_title["Security Engineer"].external_id == _C
    assert by_title["Security Engineer"].location == "Lisbon"
    assert by_title["Security Engineer"].url.endswith(_PATH_C)
    assert by_title["Data Engineer"].external_id == _D
    assert by_title["Product Manager"].external_id == _E


def test_cryptojobs_parser_ignores_non_posting_links() -> None:
    """Only Crypto Jobs detail links should become candidates."""

    adapter = CryptojobsAdapter(user_agent="test-agent")
    nav_only_html = f"""
    <a href="/crypto-jobs">Index</a>
    <a href="/web3">Index</a>
    <a href="/positions">Index</a>
    <a href="/jobs">Index</a>
    <a href="/job">Index</a>
    <a href="{_PATH_A}/apply">Apply</a>
    <a href="/crypto-jobs/{_A}/login">Login</a>
    <a href="/positions/{_C}/apply">Apply role</a>
    <a href="/about">About</a>
    <a href="/index">Index</a>
    <a href="/login">Login home</a>
    """
    jobs = adapter._parse_html(
        "https://cryptojobslist.com",
        nav_only_html,
        max_jobs=10,
    )

    assert jobs == []


def test_cryptojobs_parser_falls_back_to_title_attribute() -> None:
    """Empty anchor text should fall back to title attributes."""

    adapter = CryptojobsAdapter(user_agent="test-agent")
    html = f"""
    <a href="{_PATH_A}" title="Attr Title" data-location="Remote"></a>
    <a href="{_PATH_B}" aria-label="Aria Title" data-location="Lisbon"></a>
    """
    jobs = adapter._parse_html(
        "https://cryptojobslist.com",
        html,
        max_jobs=10,
    )

    by_title = {job.title: job for job in jobs}
    assert by_title["Attr Title"].external_id == _A
    assert by_title["Attr Title"].location == "Remote"
    assert by_title["Aria Title"].external_id == _B
    assert by_title["Aria Title"].location == "Lisbon"


def test_cryptojobs_parser_respects_max_jobs() -> None:
    """Parser should stop once max_jobs candidates are collected."""

    adapter = CryptojobsAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://cryptojobslist.com",
        Cryptojobs_SAMPLE_HTML,
        max_jobs=2,
    )

    assert len(jobs) == 2


def test_cryptojobs_parser_returns_empty_for_non_positive_max_jobs() -> None:
    """Non-positive max_jobs should short-circuit to an empty list."""

    adapter = CryptojobsAdapter(user_agent="test-agent")
    assert (
        adapter._parse_html(
            "https://cryptojobslist.com",
            Cryptojobs_SAMPLE_HTML,
            max_jobs=0,
        )
        == []
    )
    assert (
        adapter._parse_html(
            "https://cryptojobslist.com",
            Cryptojobs_SAMPLE_HTML,
            max_jobs=-1,
        )
        == []
    )


def test_cryptojobs_parser_uses_remote_flag() -> None:
    """data-remote=true should resolve location to Remote."""

    adapter = CryptojobsAdapter(user_agent="test-agent")
    html = f"""
    <a href="{_PATH_A}" data-remote="true">Remote Role</a>
    """
    jobs = adapter._parse_html("https://cryptojobslist.com", html, max_jobs=10)
    assert len(jobs) == 1
    assert jobs[0].location == "Remote"

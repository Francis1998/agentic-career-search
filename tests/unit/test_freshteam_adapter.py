"""Unit tests for the Freshteam careers site adapter."""

from __future__ import annotations

from autoapply_agent.adapters.freshteam import FreshteamAdapter

FRESHTEAM_SAMPLE_HTML = """
<html>
  <body>
    <section class="openings">
      <article class="job">
        <a href="/jobs/srhxZvjdJ2X-/executive-l-d"
           class="heading"
           data-portal-location="Bengaluru, India"
           data-portal-remote-location="false">
          Executive : L&amp;D
        </a>
      </article>
      <article class="job">
        <a href="/jobs/aQOc95c23C-j/accounting-clerk?ft_source=4000096128"
           class="heading"
           data-portal-location="Remote"
           data-portal-remote-location="true">
          Accounting Clerk
        </a>
      </article>
    </section>
    <a href="/jobs">All jobs</a>
    <a href="/jobs/srhxZvjdJ2X-/executive-l-d/apply">Apply</a>
    <a href="/about">About</a>
  </body>
</html>
"""


def test_freshteam_parser_extracts_jobs() -> None:
    """Freshteam parser should extract posting fields and skip nav/apply links."""

    adapter = FreshteamAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://foodsafetyworks.freshteam.com/jobs",
        FRESHTEAM_SAMPLE_HTML,
        max_jobs=10,
    )

    by_title = {job.title: job for job in jobs}
    assert set(by_title) == {"Executive : L&D", "Accounting Clerk"}
    assert by_title["Executive : L&D"].external_id == "srhxZvjdJ2X-"
    assert by_title["Executive : L&D"].location == "Bengaluru, India"
    assert by_title["Executive : L&D"].url == (
        "https://foodsafetyworks.freshteam.com/jobs/srhxZvjdJ2X-/executive-l-d"
    )
    assert by_title["Accounting Clerk"].external_id == "aQOc95c23C-j"
    assert by_title["Accounting Clerk"].location == "Remote"
    assert by_title["Accounting Clerk"].url.endswith(
        "/jobs/aQOc95c23C-j/accounting-clerk?ft_source=4000096128"
    )


def test_freshteam_parser_ignores_non_posting_links() -> None:
    """Only Freshteam detail links should become candidates."""

    adapter = FreshteamAdapter(user_agent="test-agent")
    nav_only_html = """
    <a href="/jobs">All jobs</a>
    <a href="/jobs/srhxZvjdJ2X-/executive-l-d/apply">Apply</a>
    <a href="/jobs/srhxZvjdJ2X-/application">Application</a>
    <a href="/people">People</a>
    """
    jobs = adapter._parse_html(
        "https://foodsafetyworks.freshteam.com/jobs",
        nav_only_html,
        max_jobs=10,
    )

    assert jobs == []


def test_freshteam_parser_falls_back_to_title_attribute() -> None:
    """Icon-only posting anchors should still yield a title attribute."""

    adapter = FreshteamAdapter(user_agent="test-agent")
    html = """
    <div class="job">
      <a href="/jobs/AbCdEf123456/staff-platform-engineer"
         title="Staff Platform Engineer"
         data-portal-remote-location="true"></a>
    </div>
    """
    jobs = adapter._parse_html("https://acme.freshteam.com/jobs", html, max_jobs=10)

    assert len(jobs) == 1
    assert jobs[0].external_id == "AbCdEf123456"
    assert jobs[0].title == "Staff Platform Engineer"
    assert jobs[0].location == "Remote"


def test_freshteam_parser_honors_zero_max_jobs() -> None:
    """A non-positive max_jobs must yield no candidates."""

    adapter = FreshteamAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://foodsafetyworks.freshteam.com/jobs",
        FRESHTEAM_SAMPLE_HTML,
        max_jobs=0,
    )

    assert jobs == []


def test_freshteam_location_is_scoped_to_its_posting() -> None:
    """A posting without its own location must not inherit a sibling's location."""

    adapter = FreshteamAdapter(user_agent="test-agent")
    html = """
    <div class="job">
      <a href="/jobs/first123456/first-role"><h4>First Role</h4></a>
    </div>
    <div class="job">
      <a href="/jobs/second123456/second-role"><h4>Second Role</h4></a>
      <span class="job-location">Berlin</span>
    </div>
    """
    jobs = adapter._parse_html("https://acme.freshteam.com/jobs", html, max_jobs=10)

    by_title = {job.title: job for job in jobs}
    assert by_title["First Role"].location is None
    assert by_title["Second Role"].location == "Berlin"

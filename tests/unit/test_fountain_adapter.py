"""Unit tests for the Fountain careers site adapter."""

from __future__ import annotations

from autoapply_agent.adapters.fountain import FountainAdapter

_POS_A = "senior-infra-abc123"
_POS_B = "platform-eng-def456"
_POS_C = "job789"
_PATH_A = f"/apply/acme-corp/{_POS_A}"
_PATH_B = f"https://web.fountain.com/apply/acme-corp/{_POS_B}"
_PATH_C = f"/jobs/{_POS_C}"

FOUNTAIN_SAMPLE_HTML = f"""
<html>
  <body>
    <section class="openings">
      <article class="job">
        <a href="{_PATH_A}"
           class="heading"
           data-location="Remote">
          Senior Infrastructure Engineer
        </a>
      </article>
      <article class="job">
        <a href="{_PATH_B}"
           class="heading"
           data-location="Poland">
          Platform Engineer
        </a>
      </article>
      <article class="job">
        <a href="{_PATH_C}"
           class="heading"
           data-job-location="London, UK">
          Customer Success Manager
        </a>
      </article>
      <article class="job">
        <a href="/openings/open001"
           class="heading"
           data-location="Berlin">
          Warehouse Associate
        </a>
      </article>
    </section>
    <a href="/apply">All jobs</a>
    <a href="{_PATH_A}/confirmation">Confirmation</a>
    <a href="/about">About</a>
  </body>
</html>
"""


def test_fountain_parser_extracts_jobs() -> None:
    """Fountain parser should extract posting fields and skip nav/apply links."""

    adapter = FountainAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://acme.fountain.com/",
        FOUNTAIN_SAMPLE_HTML,
        max_jobs=10,
    )

    by_title = {job.title: job for job in jobs}
    assert set(by_title) == {
        "Senior Infrastructure Engineer",
        "Platform Engineer",
        "Customer Success Manager",
        "Warehouse Associate",
    }
    assert by_title["Senior Infrastructure Engineer"].external_id == _POS_A
    assert by_title["Senior Infrastructure Engineer"].location == "Remote"
    assert by_title["Senior Infrastructure Engineer"].url == (f"https://acme.fountain.com{_PATH_A}")
    assert by_title["Platform Engineer"].external_id == _POS_B
    assert by_title["Platform Engineer"].location == "Poland"
    assert by_title["Customer Success Manager"].external_id == _POS_C
    assert by_title["Customer Success Manager"].location == "London, UK"
    assert by_title["Customer Success Manager"].url.endswith(_PATH_C)
    assert by_title["Warehouse Associate"].external_id == "open001"
    assert by_title["Warehouse Associate"].location == "Berlin"


def test_fountain_parser_ignores_non_posting_links() -> None:
    """Only Fountain detail links should become candidates."""

    adapter = FountainAdapter(user_agent="test-agent")
    nav_only_html = f"""
    <a href="/apply">All jobs</a>
    <a href="/apply/acme-corp">Company index</a>
    <a href="https://web.fountain.com/apply/acme-corp">Company index</a>
    <a href="{_PATH_A}/confirmation">Confirmation</a>
    <a href="{_PATH_A}/apply">Apply</a>
    <a href="/jobs/{_POS_C}/application">Application</a>
    <a href="/about">About</a>
    <a href="/login">Login</a>
    """
    jobs = adapter._parse_html(
        "https://acme.fountain.com/",
        nav_only_html,
        max_jobs=10,
    )

    assert jobs == []


def test_fountain_parser_falls_back_to_title_attribute() -> None:
    """Icon-only posting anchors should still yield a title attribute."""

    adapter = FountainAdapter(user_agent="test-agent")
    position_id = "staff-platform-xyz999"
    html = f"""
    <div class="job">
      <a href="/apply/{position_id}"
         title="Staff Platform Engineer"
         data-remote="true"></a>
    </div>
    """
    jobs = adapter._parse_html("https://acme.fountain.com/", html, max_jobs=10)

    assert len(jobs) == 1
    assert jobs[0].external_id == position_id
    assert jobs[0].title == "Staff Platform Engineer"
    assert jobs[0].location == "Remote"


def test_fountain_parser_honors_zero_max_jobs() -> None:
    """A non-positive max_jobs must yield no candidates."""

    adapter = FountainAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://acme.fountain.com/",
        FOUNTAIN_SAMPLE_HTML,
        max_jobs=0,
    )

    assert jobs == []


def test_fountain_location_is_scoped_to_its_posting() -> None:
    """A posting without its own location must not inherit a sibling's location."""

    adapter = FountainAdapter(user_agent="test-agent")
    html = """
    <div class="job">
      <a href="/positions/pos111"><h4>First Role</h4></a>
    </div>
    <div class="job">
      <a href="/positions/pos222"><h4>Second Role</h4></a>
      <span class="job-location">Berlin</span>
    </div>
    """
    jobs = adapter._parse_html("https://acme.fountain.com/", html, max_jobs=10)

    by_title = {job.title: job for job in jobs}
    assert by_title["First Role"].location is None
    assert by_title["Second Role"].location == "Berlin"


def test_fountain_parser_deduplicates_urls() -> None:
    """Duplicate posting anchors must collapse to a single candidate."""

    adapter = FountainAdapter(user_agent="test-agent")
    html = f"""
    <a href="{_PATH_A}">Engineer</a>
    <a href="{_PATH_A}">Engineer again</a>
    """
    jobs = adapter._parse_html("https://acme.fountain.com/", html, max_jobs=10)

    assert len(jobs) == 1
    assert jobs[0].title == "Engineer"

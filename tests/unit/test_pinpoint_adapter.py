"""Unit tests for the Pinpoint HR careers site adapter."""

from __future__ import annotations

from autoapply_agent.adapters.pinpoint import PinpointAdapter

PINPOINT_SAMPLE_HTML = """
<html>
  <body>
    <section class="openings">
      <article class="job">
        <a href="/postings/baa10d0a-1485-472b-a813-89a6688e4e97"
           class="heading"
           data-location="Remote">
          Senior Infrastructure Engineer
        </a>
      </article>
      <article class="job">
        <a href="/en/postings/7dcb7727-4fe1-47d6-bb17-82636428b228"
           class="heading"
           data-location="Poland">
          Platform Engineer
        </a>
      </article>
      <article class="job">
        <a href="/jobs/53913/customer-success-manager"
           class="heading"
           data-job-location="London, UK">
          Customer Success Manager
        </a>
      </article>
    </section>
    <a href="/postings">All jobs</a>
    <a href="/postings/baa10d0a-1485-472b-a813-89a6688e4e97/apply">Apply</a>
    <a href="/about">About</a>
  </body>
</html>
"""


def test_pinpoint_parser_extracts_jobs() -> None:
    """Pinpoint parser should extract posting fields and skip nav/apply links."""

    adapter = PinpointAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://workwithus.pinpointhq.com/",
        PINPOINT_SAMPLE_HTML,
        max_jobs=10,
    )

    by_title = {job.title: job for job in jobs}
    assert set(by_title) == {
        "Senior Infrastructure Engineer",
        "Platform Engineer",
        "Customer Success Manager",
    }
    assert by_title["Senior Infrastructure Engineer"].external_id == (
        "baa10d0a-1485-472b-a813-89a6688e4e97"
    )
    assert by_title["Senior Infrastructure Engineer"].location == "Remote"
    assert by_title["Senior Infrastructure Engineer"].url == (
        "https://workwithus.pinpointhq.com/postings/baa10d0a-1485-472b-a813-89a6688e4e97"
    )
    assert by_title["Platform Engineer"].external_id == "7dcb7727-4fe1-47d6-bb17-82636428b228"
    assert by_title["Platform Engineer"].location == "Poland"
    assert by_title["Customer Success Manager"].external_id == "53913"
    assert by_title["Customer Success Manager"].location == "London, UK"
    assert by_title["Customer Success Manager"].url.endswith("/jobs/53913/customer-success-manager")


def test_pinpoint_parser_ignores_non_posting_links() -> None:
    """Only Pinpoint detail links should become candidates."""

    adapter = PinpointAdapter(user_agent="test-agent")
    nav_only_html = """
    <a href="/postings">All jobs</a>
    <a href="/postings/baa10d0a-1485-472b-a813-89a6688e4e97/apply">Apply</a>
    <a href="/jobs/53913/application">Application</a>
    <a href="/about">About</a>
    """
    jobs = adapter._parse_html(
        "https://workwithus.pinpointhq.com/",
        nav_only_html,
        max_jobs=10,
    )

    assert jobs == []


def test_pinpoint_parser_falls_back_to_title_attribute() -> None:
    """Icon-only posting anchors should still yield a title attribute."""

    adapter = PinpointAdapter(user_agent="test-agent")
    html = """
    <div class="job">
      <a href="/postings/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
         title="Staff Platform Engineer"
         data-remote="true"></a>
    </div>
    """
    jobs = adapter._parse_html("https://acme.pinpointhq.com/", html, max_jobs=10)

    assert len(jobs) == 1
    assert jobs[0].external_id == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    assert jobs[0].title == "Staff Platform Engineer"
    assert jobs[0].location == "Remote"


def test_pinpoint_parser_honors_zero_max_jobs() -> None:
    """A non-positive max_jobs must yield no candidates."""

    adapter = PinpointAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://workwithus.pinpointhq.com/",
        PINPOINT_SAMPLE_HTML,
        max_jobs=0,
    )

    assert jobs == []


def test_pinpoint_location_is_scoped_to_its_posting() -> None:
    """A posting without its own location must not inherit a sibling's location."""

    adapter = PinpointAdapter(user_agent="test-agent")
    html = """
    <div class="job">
      <a href="/postings/11111111-1111-1111-1111-111111111111"><h4>First Role</h4></a>
    </div>
    <div class="job">
      <a href="/jobs/22222"><h4>Second Role</h4></a>
      <span class="job-location">Berlin</span>
    </div>
    """
    jobs = adapter._parse_html("https://acme.pinpointhq.com/", html, max_jobs=10)

    by_title = {job.title: job for job in jobs}
    assert by_title["First Role"].location is None
    assert by_title["Second Role"].location == "Berlin"


def test_pinpoint_parser_deduplicates_urls() -> None:
    """Duplicate posting anchors must collapse to a single candidate."""

    adapter = PinpointAdapter(user_agent="test-agent")
    html = """
    <a href="/postings/baa10d0a-1485-472b-a813-89a6688e4e97">Engineer</a>
    <a href="/postings/baa10d0a-1485-472b-a813-89a6688e4e97">Engineer again</a>
    """
    jobs = adapter._parse_html("https://acme.pinpointhq.com/", html, max_jobs=10)

    assert len(jobs) == 1
    assert jobs[0].title == "Engineer"

"""Unit tests for the Breezy HR careers site adapter."""

from __future__ import annotations

from autoapply_agent.adapters.breezyhr import BreezyHrAdapter

BREEZYHR_SAMPLE_HTML = """
<html>
  <body>
    <ul class="positions">
      <li class="position">
        <a href="/p/8f092b537498">Senior Backend Engineer</a>
        <span class="position-location">Remote (US)</span>
      </li>
      <li class="position">
        <a href="/p/a1b2c3d4e5f6-product-manager">Product Manager</a>
        <span class="position-location">Austin, TX</span>
      </li>
    </ul>
    <a href="/">All positions</a>
    <a href="/about">About</a>
    <a href="https://example.com/careers">Careers</a>
  </body>
</html>
"""


def test_breezyhr_parser_extracts_jobs() -> None:
    """Breezy HR parser should extract posting fields and skip nav links."""

    adapter = BreezyHrAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://acme.breezy.hr/",
        BREEZYHR_SAMPLE_HTML,
        max_jobs=10,
    )

    by_title = {job.title: job for job in jobs}
    assert set(by_title) == {"Senior Backend Engineer", "Product Manager"}
    assert by_title["Senior Backend Engineer"].external_id == "8f092b537498"
    assert by_title["Senior Backend Engineer"].location == "Remote (US)"
    assert by_title["Senior Backend Engineer"].url == ("https://acme.breezy.hr/p/8f092b537498")
    assert by_title["Product Manager"].external_id == "a1b2c3d4e5f6"
    assert by_title["Product Manager"].location == "Austin, TX"
    assert by_title["Product Manager"].url == (
        "https://acme.breezy.hr/p/a1b2c3d4e5f6-product-manager"
    )


def test_breezyhr_parser_ignores_non_posting_links() -> None:
    """Only anchors with a terminal ``p/{positionId}`` segment are postings.

    Breezy careers sites render navigation links and the application step
    (``/p/{positionId}/apply``) alongside postings. Those must be ignored so
    they do not surface as phantom candidates.
    """

    adapter = BreezyHrAdapter(user_agent="test-agent")
    nav_only_html = """
    <a href="/">All positions</a>
    <a href="/about">About</a>
    <a href="/p/8f092b537498/apply">Apply</a>
    <a href="https://example.com/careers">Careers</a>
    """
    jobs = adapter._parse_html("https://acme.breezy.hr/", nav_only_html, max_jobs=10)

    assert jobs == []


def test_breezyhr_parser_falls_back_to_title_attribute() -> None:
    """Icon-only anchors should still yield a title via the ``title`` attribute."""

    adapter = BreezyHrAdapter(user_agent="test-agent")
    html = (
        '<div class="position">'
        '<a href="/p/deadbeefcafe" title="Staff Platform Engineer"></a>'
        '<span class="position-location">Remote</span>'
        "</div>"
    )
    jobs = adapter._parse_html("https://acme.breezy.hr/", html, max_jobs=10)

    assert len(jobs) == 1
    assert jobs[0].external_id == "deadbeefcafe"
    assert jobs[0].title == "Staff Platform Engineer"
    assert jobs[0].location == "Remote"


def test_breezyhr_parser_honors_zero_max_jobs() -> None:
    """A non-positive max_jobs must yield no candidates, not one."""

    adapter = BreezyHrAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://acme.breezy.hr/",
        BREEZYHR_SAMPLE_HTML,
        max_jobs=0,
    )

    assert jobs == []


def test_breezyhr_location_is_scoped_to_its_posting() -> None:
    """A posting without its own location must not inherit a sibling's location."""

    adapter = BreezyHrAdapter(user_agent="test-agent")
    html = """
    <div class="position">
      <a href="/p/111aaa222bbb"><h4>First Role</h4></a>
    </div>
    <div class="position">
      <a href="/p/333ccc444ddd"><h4>Second Role</h4></a>
      <span class="position-location">Berlin</span>
    </div>
    """
    jobs = adapter._parse_html("https://acme.breezy.hr/", html, max_jobs=10)

    by_title = {job.title: job for job in jobs}
    assert by_title["First Role"].location is None
    assert by_title["Second Role"].location == "Berlin"

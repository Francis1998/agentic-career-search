"""Unit tests for the Teamtailor careers site adapter."""

from __future__ import annotations

from autoapply_agent.adapters.teamtailor import TeamtailorAdapter

TEAMTAILOR_SAMPLE_HTML = """
<html>
  <body>
    <ul class=\"jobs-list\">
      <li class=\"job\">
        <a href=\"/jobs/3681317-senior-backend-engineer\">Senior Backend Engineer</a>
        <span class=\"job-location\">Remote (EU)</span>
      </li>
      <li class=\"job\">
        <a href=\"/jobs/4210099-product-manager\">Product Manager</a>
        <span class=\"job-location\">London, UK</span>
      </li>
    </ul>
    <a href=\"/jobs\">All jobs</a>
    <a href=\"/connect\">Connect</a>
    <a href=\"https://example.com/about\">About</a>
  </body>
</html>
"""


def test_teamtailor_parser_extracts_jobs() -> None:
    """Teamtailor parser should extract posting fields and skip nav links."""

    adapter = TeamtailorAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://example.teamtailor.com/jobs",
        TEAMTAILOR_SAMPLE_HTML,
        max_jobs=10,
    )

    by_title = {job.title: job for job in jobs}
    assert set(by_title) == {"Senior Backend Engineer", "Product Manager"}
    assert by_title["Senior Backend Engineer"].external_id == "3681317"
    assert by_title["Senior Backend Engineer"].location == "Remote (EU)"
    assert by_title["Senior Backend Engineer"].url == (
        "https://example.teamtailor.com/jobs/3681317-senior-backend-engineer"
    )
    assert by_title["Product Manager"].external_id == "4210099"
    assert by_title["Product Manager"].location == "London, UK"


def test_teamtailor_parser_ignores_non_posting_links() -> None:
    """Only anchors with a terminal ``jobs/{jobId}`` segment are postings.

    Teamtailor careers sites render navigation links (``/jobs`` list page,
    ``/connect``, external about pages) and the application form
    (``/jobs/{jobId}/applications/new``) alongside postings. Those must be
    ignored so they do not surface as phantom candidates; a posting is
    identified purely by a terminal numeric ``{jobId}`` segment following the
    ``jobs`` path segment.
    """

    adapter = TeamtailorAdapter(user_agent="test-agent")
    nav_only_html = """
    <a href=\"/jobs\">All jobs</a>
    <a href=\"/connect\">Connect</a>
    <a href=\"/jobs/3681317-senior-backend-engineer/applications/new\">Apply</a>
    <a href=\"https://example.com/about\">About</a>
    """
    jobs = adapter._parse_html("https://example.teamtailor.com/jobs", nav_only_html, max_jobs=10)

    assert jobs == []


def test_teamtailor_parser_supports_custom_domain_careers_prefix() -> None:
    """Custom-domain career sites nest postings under a ``/careers`` prefix.

    Teamtailor lets customers host the career site on their own domain, where
    postings render as ``example.com/careers/jobs/{jobId}-{slug}``. The adapter
    must recognise the ``jobs/{jobId}`` segment pair regardless of a leading
    path prefix.
    """

    adapter = TeamtailorAdapter(user_agent="test-agent")
    html = (
        '<div class="job">'
        '<a href="/careers/jobs/9900001-staff-data-scientist">Staff Data Scientist</a>'
        "</div>"
    )
    jobs = adapter._parse_html("https://example.com/careers/jobs", html, max_jobs=10)

    assert len(jobs) == 1
    assert jobs[0].external_id == "9900001"
    assert jobs[0].url == "https://example.com/careers/jobs/9900001-staff-data-scientist"


def test_teamtailor_parser_honors_zero_max_jobs() -> None:
    """A non-positive max_jobs must yield no candidates, not one."""

    adapter = TeamtailorAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://example.teamtailor.com/jobs",
        TEAMTAILOR_SAMPLE_HTML,
        max_jobs=0,
    )

    assert jobs == []


def test_teamtailor_location_is_scoped_to_its_posting() -> None:
    """A posting without its own location must not inherit a sibling's location."""

    adapter = TeamtailorAdapter(user_agent="test-agent")
    html = """
    <div class=\"job\">
      <a href=\"/jobs/1000001-first-role\"><h4>First Role</h4></a>
    </div>
    <div class=\"job\">
      <a href=\"/jobs/1000002-second-role\"><h4>Second Role</h4></a>
      <span class=\"job-location\">Berlin</span>
    </div>
    """
    jobs = adapter._parse_html("https://example.teamtailor.com/jobs", html, max_jobs=10)

    by_title = {job.title: job for job in jobs}
    assert by_title["First Role"].location is None
    assert by_title["Second Role"].location == "Berlin"

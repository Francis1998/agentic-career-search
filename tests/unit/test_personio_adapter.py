"""Unit tests for the Personio careers site adapter."""

from __future__ import annotations

from autoapply_agent.adapters.personio import PersonioAdapter

PERSONIO_SAMPLE_HTML = """
<html>
  <body>
    <ul class=\"jobs-list\">
      <li class=\"job\">
        <a href=\"/job/58291\">Senior Data Engineer</a>
        <span class=\"job-location\">Munich, Germany</span>
      </li>
      <li class=\"job\">
        <a href=\"/job/2623782-marketing-manager\">Marketing Manager</a>
        <span class=\"job-location\">Stuttgart, Germany</span>
      </li>
    </ul>
    <a href=\"/jobs\">All jobs</a>
    <a href=\"/about\">About</a>
    <a href=\"https://example.com/imprint\">Imprint</a>
  </body>
</html>
"""


def test_personio_parser_extracts_jobs() -> None:
    """Personio parser should extract posting fields and skip nav links."""

    adapter = PersonioAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://example.jobs.personio.com",
        PERSONIO_SAMPLE_HTML,
        max_jobs=10,
    )

    by_title = {job.title: job for job in jobs}
    assert set(by_title) == {"Senior Data Engineer", "Marketing Manager"}
    assert by_title["Senior Data Engineer"].external_id == "58291"
    assert by_title["Senior Data Engineer"].location == "Munich, Germany"
    assert by_title["Senior Data Engineer"].url == ("https://example.jobs.personio.com/job/58291")
    assert by_title["Marketing Manager"].external_id == "2623782"
    assert by_title["Marketing Manager"].location == "Stuttgart, Germany"


def test_personio_parser_ignores_non_posting_links() -> None:
    """Only anchors with a terminal singular ``job/{jobId}`` segment are postings.

    Personio careers sites render navigation links (``/jobs`` list page,
    ``/about``, external imprint pages) and the application step
    (``/job/{jobId}/apply``) alongside postings. Those must be ignored so they
    do not surface as phantom candidates; a posting is identified purely by a
    terminal numeric ``{jobId}`` segment following the singular ``job`` path
    segment.
    """

    adapter = PersonioAdapter(user_agent="test-agent")
    nav_only_html = """
    <a href=\"/jobs\">All jobs</a>
    <a href=\"/about\">About</a>
    <a href=\"/job/58291/apply\">Apply</a>
    <a href=\"https://example.com/imprint\">Imprint</a>
    """
    jobs = adapter._parse_html("https://example.jobs.personio.com", nav_only_html, max_jobs=10)

    assert jobs == []


def test_personio_parser_supports_de_domain() -> None:
    """The German ``jobs.personio.de`` domain is served by the same shape.

    Personio uses two careers domains in rotation (``jobs.personio.com`` and
    ``jobs.personio.de``); the adapter must recognise the ``job/{jobId}``
    segment pair regardless of the top-level domain.
    """

    adapter = PersonioAdapter(user_agent="test-agent")
    html = '<div class="job"><a href="/job/4103">Office Manager</a></div>'
    jobs = adapter._parse_html("https://example.jobs.personio.de", html, max_jobs=10)

    assert len(jobs) == 1
    assert jobs[0].external_id == "4103"
    assert jobs[0].url == "https://example.jobs.personio.de/job/4103"
    assert jobs[0].company == "example.jobs.personio.de"


def test_personio_parser_honors_zero_max_jobs() -> None:
    """A non-positive max_jobs must yield no candidates, not one."""

    adapter = PersonioAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://example.jobs.personio.com",
        PERSONIO_SAMPLE_HTML,
        max_jobs=0,
    )

    assert jobs == []


def test_personio_location_is_scoped_to_its_posting() -> None:
    """A posting without its own location must not inherit a sibling's location."""

    adapter = PersonioAdapter(user_agent="test-agent")
    html = """
    <div class=\"job\">
      <a href=\"/job/1000001\"><h4>First Role</h4></a>
    </div>
    <div class=\"job\">
      <a href=\"/job/1000002\"><h4>Second Role</h4></a>
      <span class=\"job-location\">Berlin</span>
    </div>
    """
    jobs = adapter._parse_html("https://example.jobs.personio.com", html, max_jobs=10)

    by_title = {job.title: job for job in jobs}
    assert by_title["First Role"].location is None
    assert by_title["Second Role"].location == "Berlin"

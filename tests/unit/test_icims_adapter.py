"""Unit tests for the iCIMS careers portal adapter."""

from __future__ import annotations

from autoapply_agent.adapters.icims import IcimsAdapter

ICIMS_SAMPLE_HTML = """
<html>
  <body>
    <ul class="iCIMS_JobsTable">
      <li class="job">
        <a class="iCIMS_Anchor" href="/jobs/2931/applications-developer/job">
          Applications Developer
        </a>
        <span class="job-location">Bethesda, Maryland</span>
      </li>
      <li class="job">
        <a class="iCIMS_Anchor" href="/jobs/1707/job" title="Technical Writer"></a>
        <span class="job-location">Remote, US</span>
      </li>
    </ul>
    <a href="/jobs/search?in_iframe=1">Search all jobs</a>
    <a href="/jobs/2931/applications-developer/login">Apply</a>
    <a href="/about">About</a>
  </body>
</html>
"""


def test_icims_parser_extracts_jobs() -> None:
    """iCIMS parser should extract posting fields and skip search/apply links."""

    adapter = IcimsAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://careers-example.icims.com/jobs/search", ICIMS_SAMPLE_HTML, max_jobs=10
    )

    by_title = {job.title: job for job in jobs}
    assert set(by_title) == {"Applications Developer", "Technical Writer"}
    assert by_title["Applications Developer"].external_id == "2931"
    assert by_title["Applications Developer"].location == "Bethesda, Maryland"
    assert by_title["Applications Developer"].url == (
        "https://careers-example.icims.com/jobs/2931/applications-developer/job"
    )
    # The slug-less /jobs/{id}/job variant is recognised, and the title falls
    # back to the anchor's ``title`` attribute when the anchor text is empty.
    assert by_title["Technical Writer"].external_id == "1707"
    assert by_title["Technical Writer"].url == ("https://careers-example.icims.com/jobs/1707/job")


def test_icims_parser_ignores_non_posting_links() -> None:
    """The /jobs/search grid, the login/apply step, and nav links are not postings."""

    adapter = IcimsAdapter(user_agent="test-agent")
    nav_only_html = """
    <a href="/jobs/search?in_iframe=1">Search all jobs</a>
    <a href="/jobs/2931/applications-developer/login">Apply</a>
    <a href="/about">About</a>
    <a href="https://example.com/imprint">Imprint</a>
    """
    jobs = adapter._parse_html(
        "https://careers-example.icims.com/jobs/search", nav_only_html, max_jobs=10
    )

    assert jobs == []


def test_icims_parser_honors_zero_max_jobs() -> None:
    """A non-positive max_jobs must yield no candidates."""

    adapter = IcimsAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://careers-example.icims.com/jobs/search", ICIMS_SAMPLE_HTML, max_jobs=0
    )

    assert jobs == []


def test_icims_location_is_scoped_to_its_posting() -> None:
    """A posting without its own location must not inherit a sibling's location."""

    adapter = IcimsAdapter(user_agent="test-agent")
    html = """
    <div class="job">
      <a href="/jobs/1001/first-role/job"><h4>First Role</h4></a>
    </div>
    <div class="job">
      <a href="/jobs/1002/second-role/job"><h4>Second Role</h4></a>
      <span class="job-location">Austin</span>
    </div>
    """
    jobs = adapter._parse_html("https://careers-example.icims.com/jobs/search", html, max_jobs=10)

    by_title = {job.title: job for job in jobs}
    assert by_title["First Role"].location is None
    assert by_title["Second Role"].location == "Austin"


def test_icims_vanity_domain_posting_is_recognised() -> None:
    """A vanity-domain proxy URL that keeps the iCIMS path shape is a posting.

    Many enterprises front iCIMS with a vanity domain (``jobs.{company}.com``)
    that proxies the same ``/jobs/{id}/{slug}/job`` path shape. The URL-shape
    matcher must recognise the posting regardless of host.
    """

    adapter = IcimsAdapter(user_agent="test-agent")
    html = """
    <div class="job">
      <a href="/jobs/5005/staff-engineer/job">Staff Engineer</a>
    </div>
    """
    jobs = adapter._parse_html("https://jobs.acme.com/careers", html, max_jobs=10)

    assert len(jobs) == 1
    assert jobs[0].external_id == "5005"
    assert jobs[0].url == "https://jobs.acme.com/jobs/5005/staff-engineer/job"

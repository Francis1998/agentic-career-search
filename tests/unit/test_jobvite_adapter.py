"""Unit tests for the Jobvite careers site adapter."""

from __future__ import annotations

from autoapply_agent.adapters.jobvite import JobviteAdapter

JOBVITE_SAMPLE_HTML = """
<html>
  <body>
    <ul class="jobs-list">
      <li class="job">
        <a href="/example/job/o0rT3fw7">Account Manager</a>
        <span class="job-location">San Mateo, California</span>
      </li>
      <li class="job">
        <a href="/careers/example/job/oxbKzfwL">Platform Engineer</a>
        <span class="job-location">Remote, US</span>
      </li>
    </ul>
    <a href="/example/jobs">All jobs</a>
    <a href="/example/job/o0rT3fw7/apply">Apply</a>
    <a href="/about">About</a>
  </body>
</html>
"""


def test_jobvite_parser_extracts_jobs() -> None:
    """Jobvite parser should extract posting fields and skip nav/apply links."""

    adapter = JobviteAdapter(user_agent="test-agent")
    jobs = adapter._parse_html("https://jobs.jobvite.com/example", JOBVITE_SAMPLE_HTML, max_jobs=10)

    by_title = {job.title: job for job in jobs}
    assert set(by_title) == {"Account Manager", "Platform Engineer"}
    assert by_title["Account Manager"].external_id == "o0rT3fw7"
    assert by_title["Account Manager"].location == "San Mateo, California"
    assert by_title["Account Manager"].url == "https://jobs.jobvite.com/example/job/o0rT3fw7"
    # The /careers/{company}/job/{id} prefixed variant is also recognised.
    assert by_title["Platform Engineer"].external_id == "oxbKzfwL"


def test_jobvite_parser_ignores_non_posting_links() -> None:
    """The plural /jobs list, the /apply step, and nav links are not postings."""

    adapter = JobviteAdapter(user_agent="test-agent")
    nav_only_html = """
    <a href="/example/jobs">All jobs</a>
    <a href="/example/job/o0rT3fw7/apply">Apply</a>
    <a href="/about">About</a>
    <a href="https://example.com/imprint">Imprint</a>
    """
    jobs = adapter._parse_html("https://jobs.jobvite.com/example", nav_only_html, max_jobs=10)

    assert jobs == []


def test_jobvite_parser_honors_zero_max_jobs() -> None:
    """A non-positive max_jobs must yield no candidates."""

    adapter = JobviteAdapter(user_agent="test-agent")
    jobs = adapter._parse_html("https://jobs.jobvite.com/example", JOBVITE_SAMPLE_HTML, max_jobs=0)

    assert jobs == []


def test_jobvite_location_is_scoped_to_its_posting() -> None:
    """A posting without its own location must not inherit a sibling's location."""

    adapter = JobviteAdapter(user_agent="test-agent")
    html = """
    <div class="job">
      <a href="/example/job/aaaa1111"><h4>First Role</h4></a>
    </div>
    <div class="job">
      <a href="/example/job/bbbb2222"><h4>Second Role</h4></a>
      <span class="job-location">Austin</span>
    </div>
    """
    jobs = adapter._parse_html("https://jobs.jobvite.com/example", html, max_jobs=10)

    by_title = {job.title: job for job in jobs}
    assert by_title["First Role"].location is None
    assert by_title["Second Role"].location == "Austin"

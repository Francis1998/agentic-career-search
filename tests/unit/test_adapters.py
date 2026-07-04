"""Unit tests for source adapter HTML parsing."""

from __future__ import annotations

from typing import TYPE_CHECKING

from autoapply_agent.adapters.base import company_from_url
from autoapply_agent.adapters.greenhouse import GreenhouseAdapter
from autoapply_agent.adapters.lever import LeverAdapter

if TYPE_CHECKING:
    from _pytest.capture import CaptureFixture
    from _pytest.fixtures import FixtureRequest
    from _pytest.logging import LogCaptureFixture
    from _pytest.monkeypatch import MonkeyPatch
    from pytest_mock.plugin import MockerFixture


GREENHOUSE_SAMPLE_HTML = """
<div class=\"opening\">
  <a href=\"/example/jobs/12345?gh_jid=12345\">Backend Engineer</a>
  <span class=\"location\">Remote</span>
</div>
"""


LEVER_SAMPLE_HTML = """
<div class=\"posting\">
  <a class=\"posting-title\" href=\"/company/jobs/abc-987\">Data Engineer</a>
  <span class=\"sort-by-location\">Austin, TX</span>
</div>
"""


def test_greenhouse_parser_extracts_jobs() -> None:
    """Greenhouse parser should extract expected candidate fields."""

    adapter = GreenhouseAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://boards.greenhouse.io/embed/job_board?for=example",
        GREENHOUSE_SAMPLE_HTML,
        max_jobs=10,
    )

    assert len(jobs) == 1
    assert jobs[0].title == "Backend Engineer"
    assert jobs[0].external_id == "12345"
    assert jobs[0].location == "Remote"


def test_lever_parser_extracts_jobs() -> None:
    """Lever parser should extract expected candidate fields."""

    adapter = LeverAdapter(user_agent="test-agent")
    jobs = adapter._parse_html("https://jobs.lever.co/company", LEVER_SAMPLE_HTML, max_jobs=10)

    assert len(jobs) == 1
    assert jobs[0].title == "Data Engineer"
    assert jobs[0].external_id == "abc-987"
    assert jobs[0].location == "Austin, TX"


def test_greenhouse_parser_honors_zero_max_jobs() -> None:
    """A non-positive max_jobs must yield no candidates, not one."""

    adapter = GreenhouseAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://boards.greenhouse.io/embed/job_board?for=example",
        GREENHOUSE_SAMPLE_HTML,
        max_jobs=0,
    )

    assert jobs == []


def test_lever_parser_honors_zero_max_jobs() -> None:
    """A non-positive max_jobs must yield no candidates, not one."""

    adapter = LeverAdapter(user_agent="test-agent")
    jobs = adapter._parse_html("https://jobs.lever.co/company", LEVER_SAMPLE_HTML, max_jobs=0)

    assert jobs == []


GREENHOUSE_SLUG_HTML = """
<div class=\"opening\">
  <a href=\"/example/jobs/senior-engineer-2024\">Senior Engineer</a>
  <span class=\"location\">Remote</span>
</div>
<div class=\"opening\">
  <a href=\"/example/jobs/98765\">Staff Engineer</a>
  <span class=\"location\">Remote</span>
</div>
"""


def test_greenhouse_external_id_ignores_embedded_slug_digits() -> None:
    """A title slug year must not be misread as a numeric job id.

    Greenhouse job ids are pure-numeric path segments (or ``gh_jid`` query
    params). A slug such as ``senior-engineer-2024`` previously yielded the
    embedded digits ``2024`` (a year), which is not an id. Only a fully numeric
    trailing segment should be treated as an external id.
    """

    adapter = GreenhouseAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://boards.greenhouse.io/example",
        GREENHOUSE_SLUG_HTML,
        max_jobs=10,
    )

    by_title = {job.title: job for job in jobs}
    assert by_title["Senior Engineer"].external_id is None
    assert by_title["Staff Engineer"].external_id == "98765"


GREENHOUSE_MISSING_LOCATION_HTML = """
<div class=\"opening\">
  <a href=\"/example/jobs/111\">First Role</a>
</div>
<div class=\"opening\">
  <a href=\"/example/jobs/222\">Second Role</a>
  <span class=\"location\">Berlin</span>
</div>
"""


def test_greenhouse_location_is_scoped_to_its_opening() -> None:
    """A posting without its own location must not inherit a sibling's location.

    Location lookup previously used ``anchor.find_next`` which scans the whole
    document forward, so an opening lacking a ``span.location`` wrongly adopted
    the location of the next opening. Location must be resolved only within the
    posting's own ``div.opening`` container.
    """

    adapter = GreenhouseAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://boards.greenhouse.io/example",
        GREENHOUSE_MISSING_LOCATION_HTML,
        max_jobs=10,
    )

    by_title = {job.title: job for job in jobs}
    assert by_title["First Role"].location is None
    assert by_title["Second Role"].location == "Berlin"


LEVER_APPLY_BUTTON_HTML = """
<div class=\"posting\">
  <a class=\"posting-title\" href=\"/company/uuid-1\"><h5>Backend Engineer</h5></a>
  <div class=\"posting-apply\">
    <a class=\"posting-btn-submit\" href=\"/company/uuid-1/apply\">Apply</a>
  </div>
</div>
"""


def test_lever_parser_ignores_apply_button_anchor() -> None:
    """The per-posting apply button must not be parsed as a separate job.

    Lever list pages render an ``Apply`` anchor inside every ``div.posting``
    whose href is the posting URL with a trailing ``/apply`` segment. The
    ``div.posting a`` selector previously collected it, yielding a phantom
    candidate titled ``Apply`` that duplicated the real posting's location.
    Only the genuine posting anchor should survive.
    """

    adapter = LeverAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://jobs.lever.co/company",
        LEVER_APPLY_BUTTON_HTML,
        max_jobs=10,
    )

    assert len(jobs) == 1
    assert jobs[0].title == "Backend Engineer"
    assert jobs[0].url == "https://jobs.lever.co/company/uuid-1"


def test_company_from_url_strips_only_leading_www() -> None:
    """Only a leading ``www.`` prefix should be stripped from the host.

    A host that carries ``www`` as a non-leading DNS label (for example
    ``careers.www.acme.com``) must be preserved verbatim. The previous
    implementation used ``str.replace`` which removed the ``www.`` substring
    anywhere in the host, corrupting such identifiers.
    """

    assert company_from_url("https://www.acme.com/jobs") == "acme.com"
    assert company_from_url("https://careers.www.acme.com/jobs") == "careers.www.acme.com"

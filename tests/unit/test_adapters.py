"""Unit tests for source adapter HTML parsing."""

from __future__ import annotations

from typing import TYPE_CHECKING

from autoapply_agent.adapters.ashby import AshbyAdapter
from autoapply_agent.adapters.base import company_from_url
from autoapply_agent.adapters.greenhouse import GreenhouseAdapter
from autoapply_agent.adapters.lever import LeverAdapter
from autoapply_agent.adapters.recruitee import RecruiteeAdapter
from autoapply_agent.adapters.smartrecruiters import SmartRecruitersAdapter
from autoapply_agent.adapters.teamtailor import TeamtailorAdapter
from autoapply_agent.adapters.workable import WorkableAdapter

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


LEVER_CATEGORIES_HTML = """
<div class=\"posting\">
  <a class=\"posting-title\" href=\"/company/uuid-2\"><h5>Data Scientist</h5></a>
  <div class=\"posting-categories\">
    <span class=\"sort-by-time posting-category\">Full-time</span>
    <span class=\"sort-by-location posting-category\">San Francisco</span>
  </div>
</div>
"""


def test_lever_location_prefers_specific_location_span() -> None:
    """Location must come from the location span, not the whole categories block.

    Lever nests ``span.sort-by-location`` inside ``div.posting-categories``
    beside commitment/team spans. A grouped ``select_one`` picks the element
    that appears first in document order, which is the parent categories block,
    so location previously absorbed commitment text (``Full-time San
    Francisco``). The dedicated location span must be preferred when present.
    """

    adapter = LeverAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://jobs.lever.co/company",
        LEVER_CATEGORIES_HTML,
        max_jobs=10,
    )

    assert len(jobs) == 1
    assert jobs[0].location == "San Francisco"


GREENHOUSE_NESTED_MARKUP_HTML = """
<div class=\"opening\">
  <a href=\"/example/jobs/555\">Senior <span>Backend</span> Engineer</a>
  <span class=\"location\">San <em>Francisco</em></span>
</div>
"""


def test_greenhouse_preserves_word_boundaries_in_nested_markup() -> None:
    """Nested inline elements in a title/location must not collapse words.

    Greenhouse renders some titles and locations with nested inline markup
    (for example ``Senior <span>Backend</span> Engineer``). Extracting text with
    ``get_text(strip=True)`` concatenates the child strings with no separator,
    producing ``SeniorBackendEngineer``. Text extraction must join with a space
    so adjacent words stay separated, matching the Lever adapter's behavior.
    """

    adapter = GreenhouseAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://boards.greenhouse.io/example",
        GREENHOUSE_NESTED_MARKUP_HTML,
        max_jobs=10,
    )

    assert len(jobs) == 1
    assert jobs[0].title == "Senior Backend Engineer"
    assert jobs[0].location == "San Francisco"


ASHBY_SAMPLE_HTML = """
<div class=\"job-posting\">
  <a href=\"/acme/2b1e9d4c-4f2a-4c3d-9a1b-1234567890ab\"><h3>Staff Platform Engineer</h3></a>
  <div class=\"posting-location\">Remote (US)</div>
</div>
<div class=\"job-posting\">
  <a href=\"/acme/9f8e7d6c-5b4a-4a3b-8c2d-abcdef123456\"><h3>Product Designer</h3></a>
  <div class=\"posting-location\">New York, NY</div>
</div>
<a href=\"/acme/about\">About Us</a>
<a href=\"https://acme.example.com/privacy\">Privacy</a>
"""


def test_ashby_parser_extracts_jobs() -> None:
    """Ashby parser should extract posting fields and skip nav links."""

    adapter = AshbyAdapter(user_agent="test-agent")
    jobs = adapter._parse_html("https://jobs.ashbyhq.com/acme", ASHBY_SAMPLE_HTML, max_jobs=10)

    by_title = {job.title: job for job in jobs}
    assert set(by_title) == {"Staff Platform Engineer", "Product Designer"}
    assert by_title["Staff Platform Engineer"].external_id == (
        "2b1e9d4c-4f2a-4c3d-9a1b-1234567890ab"
    )
    assert by_title["Staff Platform Engineer"].location == "Remote (US)"
    assert by_title["Staff Platform Engineer"].url == (
        "https://jobs.ashbyhq.com/acme/2b1e9d4c-4f2a-4c3d-9a1b-1234567890ab"
    )
    assert by_title["Product Designer"].location == "New York, NY"


def test_ashby_parser_ignores_non_posting_links() -> None:
    """Only anchors whose trailing path segment is a UUID are postings.

    Ashby board pages render navigation and legal links (``/acme/about``,
    external privacy pages) alongside postings. Those must be ignored so they
    do not surface as phantom job candidates; a posting is identified purely by
    its ``/{org}/{uuid}`` URL shape.
    """

    adapter = AshbyAdapter(user_agent="test-agent")
    nav_only_html = """
    <a href=\"/acme/about\">About Us</a>
    <a href=\"/acme/teams/engineering\">Engineering</a>
    <a href=\"https://acme.example.com/privacy\">Privacy</a>
    """
    jobs = adapter._parse_html("https://jobs.ashbyhq.com/acme", nav_only_html, max_jobs=10)

    assert jobs == []


def test_ashby_parser_honors_zero_max_jobs() -> None:
    """A non-positive max_jobs must yield no candidates, not one."""

    adapter = AshbyAdapter(user_agent="test-agent")
    jobs = adapter._parse_html("https://jobs.ashbyhq.com/acme", ASHBY_SAMPLE_HTML, max_jobs=0)

    assert jobs == []


def test_ashby_location_is_scoped_to_its_posting() -> None:
    """A posting without its own location must not inherit a sibling's location.

    Location lookup is scoped to each posting's own container. A posting that
    omits a location element must resolve to ``None`` rather than borrowing the
    next posting's location.
    """

    adapter = AshbyAdapter(user_agent="test-agent")
    html = """
    <div class=\"job-posting\">
      <a href=\"/acme/2b1e9d4c-4f2a-4c3d-9a1b-1234567890ab\"><h3>First Role</h3></a>
    </div>
    <div class=\"job-posting\">
      <a href=\"/acme/9f8e7d6c-5b4a-4a3b-8c2d-abcdef123456\"><h3>Second Role</h3></a>
      <div class=\"posting-location\">Berlin</div>
    </div>
    """
    jobs = adapter._parse_html("https://jobs.ashbyhq.com/acme", html, max_jobs=10)

    by_title = {job.title: job for job in jobs}
    assert by_title["First Role"].location is None
    assert by_title["Second Role"].location == "Berlin"


WORKABLE_SAMPLE_HTML = """
<div class=\"job-posting\">
  <a href=\"/acme/j/07C67F9E9F/\"><h3>Senior Backend Engineer</h3></a>
  <div class=\"job-location\">Remote (EU)</div>
</div>
<div class=\"job-posting\">
  <a href=\"/acme/j/1A2B3C4D5E/\"><h3>Product Manager</h3></a>
  <div class=\"job-location\">London, UK</div>
</div>
<a href=\"/acme/about\">About Us</a>
<a href=\"https://acme.example.com/privacy\">Privacy</a>
"""


def test_workable_parser_extracts_jobs() -> None:
    """Workable parser should extract posting fields and skip nav links."""

    adapter = WorkableAdapter(user_agent="test-agent")
    jobs = adapter._parse_html("https://apply.workable.com/acme", WORKABLE_SAMPLE_HTML, max_jobs=10)

    by_title = {job.title: job for job in jobs}
    assert set(by_title) == {"Senior Backend Engineer", "Product Manager"}
    assert by_title["Senior Backend Engineer"].external_id == "07C67F9E9F"
    assert by_title["Senior Backend Engineer"].location == "Remote (EU)"
    assert by_title["Senior Backend Engineer"].url == (
        "https://apply.workable.com/acme/j/07C67F9E9F/"
    )
    assert by_title["Product Manager"].location == "London, UK"


def test_workable_parser_ignores_non_posting_links() -> None:
    """Only anchors with a ``/j/{shortcode}`` segment pair are postings.

    Workable board pages render navigation and legal links (``/acme/about``,
    external privacy pages) alongside postings. Those must be ignored so they
    do not surface as phantom job candidates; a posting is identified purely by
    its ``/{company}/j/{shortcode}`` URL shape.
    """

    adapter = WorkableAdapter(user_agent="test-agent")
    nav_only_html = """
    <a href=\"/acme/about\">About Us</a>
    <a href=\"/acme/departments/engineering\">Engineering</a>
    <a href=\"https://acme.example.com/privacy\">Privacy</a>
    """
    jobs = adapter._parse_html("https://apply.workable.com/acme", nav_only_html, max_jobs=10)

    assert jobs == []


def test_workable_parser_honors_zero_max_jobs() -> None:
    """A non-positive max_jobs must yield no candidates, not one."""

    adapter = WorkableAdapter(user_agent="test-agent")
    jobs = adapter._parse_html("https://apply.workable.com/acme", WORKABLE_SAMPLE_HTML, max_jobs=0)

    assert jobs == []


def test_workable_location_is_scoped_to_its_posting() -> None:
    """A posting without its own location must not inherit a sibling's location."""

    adapter = WorkableAdapter(user_agent="test-agent")
    html = """
    <div class=\"job-posting\">
      <a href=\"/acme/j/07C67F9E9F/\"><h3>First Role</h3></a>
    </div>
    <div class=\"job-posting\">
      <a href=\"/acme/j/1A2B3C4D5E/\"><h3>Second Role</h3></a>
      <div class=\"job-location\">Berlin</div>
    </div>
    """
    jobs = adapter._parse_html("https://apply.workable.com/acme", html, max_jobs=10)

    by_title = {job.title: job for job in jobs}
    assert by_title["First Role"].location is None
    assert by_title["Second Role"].location == "Berlin"


def test_company_from_url_strips_only_leading_www() -> None:
    """Only a leading ``www.`` prefix should be stripped from the host.

    A host that carries ``www`` as a non-leading DNS label (for example
    ``careers.www.acme.com``) must be preserved verbatim. The previous
    implementation used ``str.replace`` which removed the ``www.`` substring
    anywhere in the host, corrupting such identifiers.
    """

    assert company_from_url("https://www.acme.com/jobs") == "acme.com"
    assert company_from_url("https://careers.www.acme.com/jobs") == "careers.www.acme.com"


GREENHOUSE_FALLBACK_HTML = """
<a href=\"/example/jobs/12345\">Backend Engineer</a>
<a href=\"/example/job_alerts\">Get Job Alerts</a>
<a href=\"/jobseekers/faq\">FAQ for Job Seekers</a>
"""


def test_greenhouse_fallback_ignores_non_posting_job_substrings() -> None:
    """Fallback matching must not treat ``/job`` substrings as postings.

    When a Greenhouse-style board omits ``.opening`` containers, the adapter
    falls back to scanning every anchor. The previous fallback accepted any
    href containing the bare substring ``/job``, so careers navigation links
    such as ``/job_alerts`` or ``/jobseekers/faq`` surfaced as phantom job
    candidates. Only anchors exposing a whole ``jobs`` path segment (or a
    ``gh_jid`` query parameter) are genuine postings.
    """

    adapter = GreenhouseAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://boards.greenhouse.io/example",
        GREENHOUSE_FALLBACK_HTML,
        max_jobs=10,
    )

    assert [job.title for job in jobs] == ["Backend Engineer"]
    assert jobs[0].external_id == "12345"


RECRUITEE_SAMPLE_HTML = """
<div class=\"offer\">
  <a href=\"/o/senior-backend-engineer\"><h3>Senior Backend Engineer</h3></a>
  <div class=\"offer-location\">Remote (EU)</div>
</div>
<div class=\"offer\">
  <a href=\"/o/product-manager\"><h3>Product Manager</h3></a>
  <div class=\"offer-location\">London, UK</div>
</div>
"""


def test_recruitee_parser_extracts_jobs() -> None:
    """Recruitee parser should extract posting fields and skip nav links."""

    adapter = RecruiteeAdapter(user_agent="test-agent")
    jobs = adapter._parse_html("https://acme.recruitee.com", RECRUITEE_SAMPLE_HTML, max_jobs=10)

    by_title = {job.title: job for job in jobs}
    assert set(by_title) == {"Senior Backend Engineer", "Product Manager"}
    assert by_title["Senior Backend Engineer"].external_id == "senior-backend-engineer"
    assert by_title["Senior Backend Engineer"].location == "Remote (EU)"
    assert by_title["Senior Backend Engineer"].url == (
        "https://acme.recruitee.com/o/senior-backend-engineer"
    )
    assert by_title["Product Manager"].location == "London, UK"


def test_recruitee_parser_ignores_non_posting_links() -> None:
    """Only anchors with an ``/o/{slug}`` segment pair are postings.

    Recruitee careers sites render navigation and legal links (``/about``,
    ``/teams/engineering``, external privacy pages) alongside postings. Those
    must be ignored so they do not surface as phantom job candidates; a posting
    is identified purely by its ``/o/{slug}`` URL shape.
    """

    adapter = RecruiteeAdapter(user_agent="test-agent")
    nav_only_html = """
    <a href=\"/about\">About Us</a>
    <a href=\"/teams/engineering\">Engineering</a>
    <a href=\"https://acme.example.com/privacy\">Privacy</a>
    """
    jobs = adapter._parse_html("https://acme.recruitee.com", nav_only_html, max_jobs=10)

    assert jobs == []


def test_recruitee_parser_honors_zero_max_jobs() -> None:
    """A non-positive max_jobs must yield no candidates, not one."""

    adapter = RecruiteeAdapter(user_agent="test-agent")
    jobs = adapter._parse_html("https://acme.recruitee.com", RECRUITEE_SAMPLE_HTML, max_jobs=0)

    assert jobs == []


def test_recruitee_location_is_scoped_to_its_posting() -> None:
    """A posting without its own location must not inherit a sibling's location."""

    adapter = RecruiteeAdapter(user_agent="test-agent")
    html = """
    <div class=\"offer\">
      <a href=\"/o/first-role\"><h3>First Role</h3></a>
    </div>
    <div class=\"offer\">
      <a href=\"/o/second-role\"><h3>Second Role</h3></a>
      <div class=\"offer-location\">Berlin</div>
    </div>
    """
    jobs = adapter._parse_html("https://acme.recruitee.com", html, max_jobs=10)

    by_title = {job.title: job for job in jobs}
    assert by_title["First Role"].location is None
    assert by_title["Second Role"].location == "Berlin"


LEVER_CLIENT_RENDERED_HTML = """
<div class=\"postings-group\">
  <a href=\"https://jobs.lever.co/company/11111111-1111-4111-8111-111111111111\">
    Backend Engineer
  </a>
  <a href=\"https://jobs.lever.co/company/22222222-2222-4222-8222-222222222222\">
    Frontend Engineer
  </a>
  <a href=\"https://jobs.lever.co/company\">All Jobs</a>
  <a href=\"https://jobs.lever.co/company/11111111-1111-4111-8111-111111111111/apply\">
    Apply
  </a>
</div>
"""


def test_lever_fallback_recognizes_uuid_posting_urls() -> None:
    """Fallback must recognise real Lever ``/{company}/{uuid}`` posting URLs.

    When the primary ``div.posting`` selector is absent (alternative or
    client-rendered board markup), the fallback previously searched for a
    ``/jobs/`` path segment that real Lever posting URLs never contain, so no
    postings were surfaced. The fallback must instead recognise the true
    trailing-UUID posting shape while ignoring the board index link and the
    per-posting ``/apply`` action anchor.
    """

    adapter = LeverAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://jobs.lever.co/company",
        LEVER_CLIENT_RENDERED_HTML,
        max_jobs=10,
    )

    assert {job.url for job in jobs} == {
        "https://jobs.lever.co/company/11111111-1111-4111-8111-111111111111",
        "https://jobs.lever.co/company/22222222-2222-4222-8222-222222222222",
    }
    assert {job.title for job in jobs} == {"Backend Engineer", "Frontend Engineer"}


SMARTRECRUITERS_SAMPLE_HTML = """
<div class=\"opening-job\">
  <a href=\"/ExampleCompany/744000123456789-senior-backend-engineer\">
    <h4>Senior Backend Engineer</h4>
  </a>
  <span class=\"job-location\">Remote (EU)</span>
</div>
<div class=\"opening-job\">
  <a href=\"/ExampleCompany/744000987654321\">Product Manager</a>
  <span class=\"job-location\">London, UK</span>
</div>
<a href=\"/ExampleCompany\">All Openings</a>
<a href=\"/ExampleCompany/search\">Search</a>
<a href=\"https://example.com/privacy\">Privacy</a>
"""


def test_smartrecruiters_parser_extracts_jobs() -> None:
    """SmartRecruiters parser should extract posting fields and skip nav links."""

    adapter = SmartRecruitersAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://jobs.smartrecruiters.com/ExampleCompany",
        SMARTRECRUITERS_SAMPLE_HTML,
        max_jobs=10,
    )

    by_title = {job.title: job for job in jobs}
    assert set(by_title) == {"Senior Backend Engineer", "Product Manager"}
    assert by_title["Senior Backend Engineer"].external_id == "744000123456789"
    assert by_title["Senior Backend Engineer"].location == "Remote (EU)"
    assert by_title["Senior Backend Engineer"].url == (
        "https://jobs.smartrecruiters.com/ExampleCompany/744000123456789-senior-backend-engineer"
    )
    assert by_title["Product Manager"].external_id == "744000987654321"
    assert by_title["Product Manager"].location == "London, UK"


def test_smartrecruiters_parser_ignores_non_posting_links() -> None:
    """Only anchors with a numeric ``{jobId}`` segment are postings.

    SmartRecruiters careers sites render navigation and legal links
    (``/ExampleCompany``, ``/ExampleCompany/search``, external privacy pages)
    alongside postings. Those must be ignored so they do not surface as phantom
    job candidates; a posting is identified purely by its numeric ``{jobId}``
    path segment.
    """

    adapter = SmartRecruitersAdapter(user_agent="test-agent")
    nav_only_html = """
    <a href=\"/ExampleCompany\">All Openings</a>
    <a href=\"/ExampleCompany/search\">Search</a>
    <a href=\"https://example.com/privacy\">Privacy</a>
    """
    jobs = adapter._parse_html(
        "https://jobs.smartrecruiters.com/ExampleCompany", nav_only_html, max_jobs=10
    )

    assert jobs == []


def test_smartrecruiters_parser_honors_zero_max_jobs() -> None:
    """A non-positive max_jobs must yield no candidates, not one."""

    adapter = SmartRecruitersAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://jobs.smartrecruiters.com/ExampleCompany",
        SMARTRECRUITERS_SAMPLE_HTML,
        max_jobs=0,
    )

    assert jobs == []


def test_smartrecruiters_location_is_scoped_to_its_posting() -> None:
    """A posting without its own location must not inherit a sibling's location."""

    adapter = SmartRecruitersAdapter(user_agent="test-agent")
    html = """
    <div class=\"opening-job\">
      <a href=\"/ExampleCompany/744000111111111\"><h4>First Role</h4></a>
    </div>
    <div class=\"opening-job\">
      <a href=\"/ExampleCompany/744000222222222\"><h4>Second Role</h4></a>
      <span class=\"job-location\">Berlin</span>
    </div>
    """
    jobs = adapter._parse_html("https://jobs.smartrecruiters.com/ExampleCompany", html, max_jobs=10)

    by_title = {job.title: job for job in jobs}
    assert by_title["First Role"].location is None
    assert by_title["Second Role"].location == "Berlin"


def test_smartrecruiters_relocation_note_is_not_read_as_location() -> None:
    """A ``relocation`` badge must not be mistaken for the posting location.

    The shared location lookup selected any element whose ``class`` merely
    *contained* the substring ``location`` (``[class*=location]``). A posting
    that advertises ``relocation`` assistance therefore surfaced that badge as
    the posting's location even though no real location element was present.
    The location must be resolved only from a class token that is actually
    ``location`` (optionally hyphen/underscore-delimited), so a posting with
    only a ``relocation`` note resolves to ``None``.
    """

    adapter = SmartRecruitersAdapter(user_agent="test-agent")
    html = """
    <div class=\"opening-job\">
      <a href=\"/ExampleCompany/744000333333333\"><h4>Relocation Role</h4></a>
      <span class=\"relocation-note\">Relocation assistance available</span>
    </div>
    """
    jobs = adapter._parse_html("https://jobs.smartrecruiters.com/ExampleCompany", html, max_jobs=10)

    assert len(jobs) == 1
    assert jobs[0].location is None


def test_teamtailor_relocation_note_is_not_read_as_location() -> None:
    """A ``relocation`` badge must not be mistaken for a Teamtailor location.

    Regression guard mirroring
    ``test_smartrecruiters_relocation_note_is_not_read_as_location`` for the
    Teamtailor adapter, which shares the same location-resolution helper.
    """

    adapter = TeamtailorAdapter(user_agent="test-agent")
    html = """
    <div class=\"job\">
      <a href=\"/jobs/1000003-relocation-role\"><h4>Relocation Role</h4></a>
      <span class=\"relocation-note\">Relocation assistance available</span>
    </div>
    """
    jobs = adapter._parse_html("https://example.teamtailor.com/jobs", html, max_jobs=10)

    assert len(jobs) == 1
    assert jobs[0].location is None

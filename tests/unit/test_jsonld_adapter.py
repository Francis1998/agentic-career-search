"""Unit tests for the schema.org JobPosting JSON-LD adapter."""

from __future__ import annotations

from typing import TYPE_CHECKING

from autoapply_agent.adapters.jsonld import JsonLdAdapter

if TYPE_CHECKING:
    from _pytest.capture import CaptureFixture
    from _pytest.fixtures import FixtureRequest
    from _pytest.logging import LogCaptureFixture
    from _pytest.monkeypatch import MonkeyPatch
    from pytest_mock.plugin import MockerFixture


SINGLE_POSTING_HTML = """
<html><head>
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "JobPosting",
  "title": "Senior ML Engineer",
  "identifier": {"@type": "PropertyValue", "name": "Acme", "value": "R-4821"},
  "hiringOrganization": {"@type": "Organization", "name": "Acme Labs"},
  "jobLocation": {
    "@type": "Place",
    "address": {
      "@type": "PostalAddress",
      "addressLocality": "San Francisco",
      "addressRegion": "CA"
    }
  },
  "url": "/careers/R-4821"
}
</script>
</head><body></body></html>
"""


def test_jsonld_parses_single_posting() -> None:
    """A single JobPosting block should map cleanly onto a candidate."""

    adapter = JsonLdAdapter(user_agent="test-agent")
    jobs = adapter._parse_html("https://acme.example.com/careers", SINGLE_POSTING_HTML, max_jobs=10)

    assert len(jobs) == 1
    job = jobs[0]
    assert job.title == "Senior ML Engineer"
    assert job.external_id == "R-4821"
    assert job.company == "Acme Labs"
    assert job.location == "San Francisco, CA"
    assert job.url == "https://acme.example.com/careers/R-4821"


GRAPH_HTML = """
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@graph": [
    {"@type": "Organization", "name": "Acme Labs"},
    {
      "@type": "JobPosting",
      "title": "Backend Engineer",
      "hiringOrganization": "Acme Labs",
      "url": "https://acme.example.com/jobs/1",
      "jobLocationType": "TELECOMMUTE"
    },
    {
      "@type": ["JobPosting", "WebPage"],
      "title": "Data Scientist",
      "url": "https://acme.example.com/jobs/2",
      "jobLocation": [
        {"@type": "Place", "address": {"addressLocality": "Berlin", "addressCountry": "DE"}}
      ]
    }
  ]
}
</script>
"""


def test_jsonld_parses_graph_and_remote_and_list_type() -> None:
    """@graph containers, TELECOMMUTE remote, and list @type are all handled."""

    adapter = JsonLdAdapter(user_agent="test-agent")
    jobs = adapter._parse_html("https://acme.example.com/careers", GRAPH_HTML, max_jobs=10)

    by_title = {job.title: job for job in jobs}
    assert set(by_title) == {"Backend Engineer", "Data Scientist"}
    assert by_title["Backend Engineer"].location == "Remote"
    assert by_title["Backend Engineer"].company == "Acme Labs"
    assert by_title["Data Scientist"].location == "Berlin, DE"


REMOTE_LIST_TYPE_HTML = """
<script type="application/ld+json">
{
  "@type": "JobPosting",
  "title": "Remote Platform Engineer",
  "url": "https://acme.example.com/jobs/remote-1",
  "jobLocationType": ["TELECOMMUTE"]
}
</script>
"""


def test_jsonld_marks_remote_when_location_type_is_a_list() -> None:
    """A list-valued ``jobLocationType`` of ``TELECOMMUTE`` must resolve to Remote.

    JSON-LD permits any property to be expressed as an array, so a remote-only
    posting may carry ``"jobLocationType": ["TELECOMMUTE"]`` instead of the
    scalar string. Such postings have no ``jobLocation`` block, so failing to
    recognise the list form leaves the location unset entirely.
    """

    adapter = JsonLdAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://acme.example.com/careers", REMOTE_LIST_TYPE_HTML, max_jobs=10
    )

    assert len(jobs) == 1
    assert jobs[0].location == "Remote"


MALFORMED_HTML = """
<script type="application/ld+json">{ this is not valid json </script>
<script type="application/ld+json">
{"@type": "JobPosting", "title": "Only Valid Role", "url": "https://acme.example.com/jobs/9"}
</script>
"""


def test_jsonld_skips_malformed_blocks() -> None:
    """A malformed JSON-LD block must not discard valid postings elsewhere."""

    adapter = JsonLdAdapter(user_agent="test-agent")
    jobs = adapter._parse_html("https://acme.example.com/careers", MALFORMED_HTML, max_jobs=10)

    assert len(jobs) == 1
    assert jobs[0].title == "Only Valid Role"
    assert jobs[0].company == "acme.example.com"


DUPLICATE_URL_HTML = """
<script type="application/ld+json">
[
  {"@type": "JobPosting", "title": "Role A", "url": "https://acme.example.com/jobs/1"},
  {"@type": "JobPosting", "title": "Role A Duplicate", "url": "https://acme.example.com/jobs/1"}
]
</script>
"""


def test_jsonld_deduplicates_by_url() -> None:
    """Postings sharing a URL should collapse to a single candidate."""

    adapter = JsonLdAdapter(user_agent="test-agent")
    jobs = adapter._parse_html("https://acme.example.com/careers", DUPLICATE_URL_HTML, max_jobs=10)

    assert len(jobs) == 1
    assert jobs[0].title == "Role A"


URLLESS_POSTINGS_HTML = """
<script type="application/ld+json">
[
  {"@type": "JobPosting", "title": "Platform Engineer"},
  {"@type": "JobPosting", "title": "Site Reliability Engineer"}
]
</script>
"""


def test_jsonld_keeps_distinct_postings_without_explicit_url() -> None:
    """Distinct postings that omit their own URL must not collapse under dedup.

    A ``JobPosting`` block need not carry a ``url``; when absent the candidate
    falls back to ``base_url``. Deduplicating solely on that shared fallback URL
    silently discarded every url-less posting after the first. Distinct roles
    must each survive, keyed apart by title.
    """

    adapter = JsonLdAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://acme.example.com/careers", URLLESS_POSTINGS_HTML, max_jobs=10
    )

    assert {job.title for job in jobs} == {"Platform Engineer", "Site Reliability Engineer"}
    assert all(job.url == "https://acme.example.com/careers" for job in jobs)


IRI_AND_CURIE_TYPE_HTML = """
<script type="application/ld+json">
{"@type": "http://schema.org/JobPosting", "title": "Staff ML Engineer",
 "url": "https://acme.example.com/jobs/iri"}
</script>
<script type="application/ld+json">
{"@type": "schema:JobPosting", "title": "Applied Scientist",
 "url": "https://acme.example.com/jobs/curie"}
</script>
<script type="application/ld+json">
{"@type": ["https://schema.org/JobPosting", "WebPage"], "title": "MLOps Engineer",
 "url": "https://acme.example.com/jobs/iri-list"}
</script>
"""


def test_jsonld_recognizes_iri_and_curie_type_forms() -> None:
    """Fully-qualified IRI and prefixed CURIE ``@type`` forms must be parsed.

    schema.org lets a ``@type`` be written as the bare term, a fully-qualified
    IRI (``https://schema.org/JobPosting``), or a context-prefixed CURIE
    (``schema:JobPosting``). Matching only the bare term silently dropped every
    posting emitted with an IRI/CURIE type, which some real applicant tracking
    systems produce. All three forms must resolve to a candidate.
    """

    adapter = JsonLdAdapter(user_agent="test-agent")
    jobs = adapter._parse_html(
        "https://acme.example.com/careers", IRI_AND_CURIE_TYPE_HTML, max_jobs=10
    )

    assert {job.title for job in jobs} == {
        "Staff ML Engineer",
        "Applied Scientist",
        "MLOps Engineer",
    }


def test_jsonld_type_term_ignores_lookalike_types() -> None:
    """A type whose local term is not exactly ``JobPosting`` must be rejected.

    Reducing an IRI/CURIE to its local term must not over-match unrelated types
    such as ``SomeJobPosting`` or ``JobPostingList`` that merely embed the term.
    """

    lookalike_html = (
        '<script type="application/ld+json">'
        '{"@type": "SomeJobPosting", "title": "Not A Posting", "url": "https://x/1"}'
        "</script>"
        '<script type="application/ld+json">'
        '{"@type": "https://schema.org/JobPostingList", "title": "Also Not", "url": "https://x/2"}'
        "</script>"
    )
    adapter = JsonLdAdapter(user_agent="test-agent")
    jobs = adapter._parse_html("https://acme.example.com/careers", lookalike_html, max_jobs=10)

    assert jobs == []


def test_jsonld_honors_zero_max_jobs() -> None:
    """A non-positive max_jobs must yield no candidates."""

    adapter = JsonLdAdapter(user_agent="test-agent")
    jobs = adapter._parse_html("https://acme.example.com/careers", SINGLE_POSTING_HTML, max_jobs=0)

    assert jobs == []

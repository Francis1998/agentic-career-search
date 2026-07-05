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


def test_jsonld_honors_zero_max_jobs() -> None:
    """A non-positive max_jobs must yield no candidates."""

    adapter = JsonLdAdapter(user_agent="test-agent")
    jobs = adapter._parse_html("https://acme.example.com/careers", SINGLE_POSTING_HTML, max_jobs=0)

    assert jobs == []

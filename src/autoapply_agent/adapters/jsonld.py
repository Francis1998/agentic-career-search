"""Generic schema.org JobPosting adapter driven by embedded JSON-LD.

Most modern applicant tracking systems (Greenhouse, Lever, Ashby,
SmartRecruiters, Workable, ...) emit `schema.org/JobPosting` structured data in
``<script type="application/ld+json">`` blocks so their postings surface in
Google Jobs. Parsing that standardized payload gives a single, vendor-neutral
adapter that works against any board publishing the contract, instead of one
bespoke DOM scraper per provider.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from autoapply_agent.adapters.base import CareerSourceAdapter, JobCandidate, company_from_url

_JOB_POSTING_TYPE = "JobPosting"
_ADDRESS_FIELDS = ("addressLocality", "addressRegion", "addressCountry")


class JsonLdAdapter(CareerSourceAdapter):
    """Extract job candidates from schema.org JobPosting JSON-LD blocks."""

    adapter_name = "jsonld"

    def __init__(self, user_agent: str) -> None:
        """Create adapter instance.

        Args:
            user_agent: HTTP user agent string.
        """

        self._user_agent = user_agent

    async def fetch_jobs(
        self, base_url: str, timeout_seconds: float, max_jobs: int
    ) -> list[JobCandidate]:
        """Fetch a page and parse embedded JobPosting JSON-LD.

        Args:
            base_url: Source URL.
            timeout_seconds: Request timeout in seconds.
            max_jobs: Maximum number of jobs.

        Returns:
            Parsed job candidates.
        """

        html = await self._request_html(base_url, timeout_seconds, self._user_agent)
        return self._parse_html(base_url, html, max_jobs)

    def _parse_html(self, base_url: str, html: str, max_jobs: int) -> list[JobCandidate]:
        """Parse JobPosting JSON-LD blocks from page HTML.

        Malformed JSON-LD blocks are skipped so a single invalid script does not
        discard valid postings elsewhere on the page.

        Args:
            base_url: Source URL.
            html: Page HTML body.
            max_jobs: Maximum number of jobs.

        Returns:
            Parsed jobs list.
        """

        if max_jobs <= 0:
            return []

        soup = BeautifulSoup(html, "html.parser")
        jobs: list[JobCandidate] = []
        seen_keys: set[tuple[str, str]] = set()
        for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
            raw_text = script.string or script.get_text()
            if not raw_text or not raw_text.strip():
                continue
            try:
                document = json.loads(raw_text)
            except (json.JSONDecodeError, ValueError):
                continue

            for node in self._iter_job_postings(document):
                candidate = self._build_candidate(base_url, node)
                if candidate is None:
                    continue
                # Postings that omit their own ``url`` all fall back to
                # ``base_url``; keying dedup solely on the URL would collapse
                # such distinct postings into one. A posting that carries its
                # own URL is still deduplicated by that URL alone (the URL is
                # the posting identity), while url-less postings are kept apart
                # by title so genuinely distinct roles all survive.
                dedup_key = (
                    (candidate.url, "")
                    if candidate.url != base_url
                    else (base_url, candidate.title)
                )
                if dedup_key in seen_keys:
                    continue
                seen_keys.add(dedup_key)
                jobs.append(candidate)
                if len(jobs) >= max_jobs:
                    return jobs

        return jobs

    @classmethod
    def _iter_job_postings(cls, node: object) -> Iterator[dict[str, object]]:
        """Yield JobPosting dicts from an arbitrarily nested JSON-LD document.

        Handles bare objects, arrays of postings, ``@graph`` containers, and
        ``ItemList`` wrappers by descending into non-JobPosting containers.

        Args:
            node: Any decoded JSON-LD fragment.

        Yields:
            Objects whose ``@type`` is (or contains) ``JobPosting``.
        """

        if isinstance(node, list):
            for item in node:
                yield from cls._iter_job_postings(item)
            return
        if not isinstance(node, dict):
            return
        if cls._is_job_posting(node):
            yield node
            return
        for key, value in node.items():
            if key == "@type":
                continue
            if isinstance(value, (list, dict)):
                yield from cls._iter_job_postings(value)

    @classmethod
    def _is_job_posting(cls, node: dict[str, object]) -> bool:
        """Report whether a JSON-LD object declares the JobPosting type.

        A ``@type`` may be expressed as the bare term (``JobPosting``), a
        fully-qualified IRI (``https://schema.org/JobPosting``), or a
        context-prefixed CURIE (``schema:JobPosting``); all three are valid
        schema.org expressions of the same type, so each must be recognised to
        avoid silently dropping otherwise valid postings.

        Args:
            node: Decoded JSON-LD object.

        Returns:
            True when ``@type`` equals or includes ``JobPosting``.
        """

        node_type = node.get("@type")
        if isinstance(node_type, str):
            return cls._type_term(node_type) == _JOB_POSTING_TYPE
        if isinstance(node_type, list):
            return any(
                isinstance(item, str) and cls._type_term(item) == _JOB_POSTING_TYPE
                for item in node_type
            )
        return False

    @staticmethod
    def _type_term(node_type: str) -> str:
        """Reduce a JSON-LD ``@type`` value to its bare local term.

        The local term is the segment after the final ``/`` (IRI form) or ``:``
        (CURIE form), so ``https://schema.org/JobPosting`` and
        ``schema:JobPosting`` both reduce to ``JobPosting`` while a bare term is
        returned unchanged.

        Args:
            node_type: A single ``@type`` string value.

        Returns:
            The local term with surrounding whitespace stripped.
        """

        term = node_type.strip()
        for separator in ("/", ":"):
            term = term.rsplit(separator, 1)[-1]
        return term

    @classmethod
    def _build_candidate(cls, base_url: str, node: dict[str, object]) -> JobCandidate | None:
        """Build a JobCandidate from a JobPosting object.

        Args:
            base_url: Source URL used for relative URL resolution and fallbacks.
            node: Decoded JobPosting object.

        Returns:
            JobCandidate when a usable title is present, else None.
        """

        title = node.get("title")
        if not isinstance(title, str) or not title.strip():
            return None

        posting_url = node.get("url")
        absolute_url = (
            urljoin(base_url, posting_url)
            if isinstance(posting_url, str) and posting_url.strip()
            else base_url
        )

        location = cls._extract_location(node.get("jobLocation"))
        if location is None and cls._is_remote(node.get("jobLocationType")):
            location = "Remote"

        company = cls._extract_company(node.get("hiringOrganization")) or company_from_url(base_url)

        return JobCandidate(
            external_id=cls._extract_identifier(node.get("identifier")),
            title=title.strip(),
            location=location,
            company=company,
            url=absolute_url,
            raw={"source": "jsonld"},
        )

    @staticmethod
    def _is_remote(job_location_type: object) -> bool:
        """Report whether a ``jobLocationType`` value denotes a remote role.

        JSON-LD permits any property to be expressed either as a scalar or as an
        array of values, so ``TELECOMMUTE`` may arrive as the bare string or
        wrapped in a list. Both forms must be recognised.

        Args:
            job_location_type: Raw ``jobLocationType`` value from a posting.

        Returns:
            True when any value equals ``TELECOMMUTE``.
        """

        if isinstance(job_location_type, str):
            return job_location_type == "TELECOMMUTE"
        if isinstance(job_location_type, list):
            return "TELECOMMUTE" in job_location_type
        return False

    @staticmethod
    def _extract_identifier(identifier: object) -> str | None:
        """Extract an external id from a schema.org identifier value.

        Args:
            identifier: Either a string or a ``PropertyValue`` object.

        Returns:
            Identifier string when present.
        """

        if isinstance(identifier, str):
            return identifier.strip() or None
        if isinstance(identifier, dict):
            value = identifier.get("value")
            if isinstance(value, (str, int)) and str(value).strip():
                return str(value).strip()
        return None

    @staticmethod
    def _extract_company(organization: object) -> str | None:
        """Extract a hiring organization name.

        Args:
            organization: Either a string or an ``Organization`` object.

        Returns:
            Company name when present.
        """

        if isinstance(organization, str):
            return organization.strip() or None
        if isinstance(organization, dict):
            name = organization.get("name")
            if isinstance(name, str) and name.strip():
                return name.strip()
        return None

    @classmethod
    def _extract_location(cls, job_location: object) -> str | None:
        """Extract a human-readable location from a jobLocation value.

        Args:
            job_location: A ``Place`` object or list of ``Place`` objects.

        Returns:
            First resolvable location string, else None.
        """

        if isinstance(job_location, list):
            for item in job_location:
                resolved = cls._place_to_string(item)
                if resolved:
                    return resolved
            return None
        return cls._place_to_string(job_location)

    @staticmethod
    def _place_to_string(place: object) -> str | None:
        """Convert a schema.org Place into a compact location string.

        Args:
            place: A ``Place`` object.

        Returns:
            ``Locality, Region, Country`` style string when derivable.
        """

        if not isinstance(place, dict):
            return None
        address = place.get("address")
        if isinstance(address, str):
            return address.strip() or None
        if not isinstance(address, dict):
            return None
        parts = [
            address[field].strip()
            for field in _ADDRESS_FIELDS
            if isinstance(address.get(field), str) and address[field].strip()
        ]
        return ", ".join(parts) or None

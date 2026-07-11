"""Teamtailor public careers site adapter.

Teamtailor (``{company}.teamtailor.com``) is a widely adopted applicant
tracking system. Its public careers site renders each posting as an anchor
whose href follows the ``/jobs/{jobId}-{slug}`` shape, where ``jobId`` is the
posting's stable numeric identifier and ``slug`` is an optional lowercase,
hyphenated title token. Custom-domain career sites reuse the same tail under a
``/careers`` prefix (``example.com/careers/jobs/{jobId}-{slug}``). This adapter
targets that structure with a primary CSS selector and a resilient fallback
that recognises posting anchors purely by their URL shape, mirroring the
greenhouse, lever, ashby, workable, recruitee, and smartrecruiters adapters.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from autoapply_agent.adapters.base import (
    CareerSourceAdapter,
    JobCandidate,
    company_from_url,
    find_location_text,
)

_JOB_ID_SEGMENT = re.compile(r"^(\d+)(?:-[a-z0-9-]+)?$")
_CONTAINER_CLASS_PATTERN = re.compile("job|posting|opening", re.IGNORECASE)


class TeamtailorAdapter(CareerSourceAdapter):
    """Fetch jobs from public Teamtailor careers site pages."""

    adapter_name = "teamtailor"

    def __init__(self, user_agent: str) -> None:
        """Create adapter instance.

        Args:
            user_agent: HTTP user agent string.
        """

        self._user_agent = user_agent

    async def fetch_jobs(
        self, base_url: str, timeout_seconds: float, max_jobs: int
    ) -> list[JobCandidate]:
        """Fetch and parse Teamtailor jobs.

        Args:
            base_url: Teamtailor careers site URL.
            timeout_seconds: Request timeout in seconds.
            max_jobs: Maximum number of jobs.

        Returns:
            Parsed job candidates.
        """

        html = await self._request_html(base_url, timeout_seconds, self._user_agent)
        return self._parse_html(base_url, html, max_jobs)

    def _parse_html(self, base_url: str, html: str, max_jobs: int) -> list[JobCandidate]:
        """Parse Teamtailor careers HTML into job candidates.

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
        anchors = [
            anchor
            for anchor in soup.select("a[href]")
            if self._is_posting_href(self._normalize_href(anchor.get("href")))
        ]

        jobs: list[JobCandidate] = []
        seen_urls: set[str] = set()
        for anchor in anchors:
            href = self._normalize_href(anchor.get("href"))
            title = anchor.get_text(" ", strip=True)
            if not href or not title:
                continue
            absolute_url = urljoin(base_url, href)
            if absolute_url in seen_urls:
                continue
            seen_urls.add(absolute_url)

            jobs.append(
                JobCandidate(
                    external_id=self._extract_external_id(absolute_url),
                    title=title,
                    location=self._extract_location(anchor),
                    company=company_from_url(base_url),
                    url=absolute_url,
                    raw={"source": "teamtailor"},
                )
            )
            if len(jobs) >= max_jobs:
                break

        return jobs

    @classmethod
    def _is_posting_href(cls, href: str | None) -> bool:
        """Report whether an href points at a Teamtailor posting.

        Teamtailor posting URLs carry a ``jobs`` path segment immediately
        followed by a numeric ``{jobId}`` segment (``/jobs/{jobId}-{slug}``),
        which must be the terminal path segment. This excludes the jobs list
        page (``/jobs``) and the application form
        (``/jobs/{jobId}/applications/new``), whose numeric id segment is not
        terminal. Careers-site navigation links never match that shape.

        Args:
            href: Candidate href value.

        Returns:
            True when the URL exposes a terminal ``jobs/{jobId}`` segment pair.
        """

        return cls._extract_external_id(href) is not None

    @staticmethod
    def _extract_external_id(job_url: str | None) -> str | None:
        """Extract the posting job id from a Teamtailor URL.

        Args:
            job_url: Teamtailor job URL or href.

        Returns:
            Numeric job id string when the terminal ``jobs/{jobId}-{slug}``
            shape is present.
        """

        if not job_url:
            return None
        parts = [part for part in urlparse(job_url).path.split("/") if part]
        for index, part in enumerate(parts):
            if part != "jobs" or index + 1 >= len(parts):
                continue
            match = _JOB_ID_SEGMENT.match(parts[index + 1])
            if match and index + 2 == len(parts):
                return match.group(1)
        return None

    @staticmethod
    def _extract_location(anchor: object) -> str | None:
        """Resolve a posting location from an anchor's surrounding markup.

        Teamtailor groups a posting's metadata (department, location) alongside
        the title anchor. The location is looked up within the anchor's nearest
        posting container so a posting without its own location does not inherit
        a sibling's location.

        Args:
            anchor: BeautifulSoup anchor element for the posting.

        Returns:
            Location text when discoverable, else None.
        """

        return find_location_text(anchor, _CONTAINER_CLASS_PATTERN)

    @staticmethod
    def _normalize_href(href_value: str | Sequence[str] | None) -> str | None:
        """Normalize BeautifulSoup href values to a single URL string.

        Args:
            href_value: Href value that can be string, list-like, or missing.

        Returns:
            Normalized URL string when present.
        """

        if isinstance(href_value, str):
            return href_value
        if isinstance(href_value, Sequence):
            for item in href_value:
                if isinstance(item, str) and item:
                    return item
        return None

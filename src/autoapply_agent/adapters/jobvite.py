"""Jobvite public careers site adapter.

Jobvite (``jobs.jobvite.com/{company}``) is a widely adopted applicant tracking
system. Its public careers site renders each posting as an anchor whose href
follows the ``/{company}/job/{jobId}`` shape (also reachable under a
``/careers/{company}/job/{jobId}`` prefix), where ``jobId`` is the posting's
stable mixed-case alphanumeric identifier (for example ``o0rT3fw7``). Note the
*singular* ``job`` path segment, which distinguishes a posting from the plural
``/{company}/jobs`` list page, and that the ``jobId`` is the terminal path
segment, which excludes the application step (``/job/{jobId}/apply``). This
adapter targets that structure with a resilient URL-shape matcher, mirroring the
greenhouse, lever, ashby, workable, recruitee, smartrecruiters, teamtailor, and
personio adapters. Jobvite ids are alphanumeric (unlike Personio's purely
numeric ids), so a dedicated matcher is used.
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

# Jobvite ids are mixed-case alphanumeric tokens (e.g. ``o0rT3fw7``); require a
# minimum length so short path words are not mistaken for a posting id.
_JOB_ID_SEGMENT = re.compile(r"^[A-Za-z0-9]{5,}$")
_CONTAINER_CLASS_PATTERN = re.compile("job|position|posting", re.IGNORECASE)


class JobviteAdapter(CareerSourceAdapter):
    """Fetch jobs from public Jobvite careers site pages."""

    adapter_name = "jobvite"

    def __init__(self, user_agent: str) -> None:
        """Create adapter instance.

        Args:
            user_agent: HTTP user agent string.
        """

        self._user_agent = user_agent

    async def fetch_jobs(
        self, base_url: str, timeout_seconds: float, max_jobs: int
    ) -> list[JobCandidate]:
        """Fetch and parse Jobvite jobs.

        Args:
            base_url: Jobvite careers site URL.
            timeout_seconds: Request timeout in seconds.
            max_jobs: Maximum number of jobs.

        Returns:
            Parsed job candidates.
        """

        html = await self._request_html(base_url, timeout_seconds, self._user_agent)
        return self._parse_html(base_url, html, max_jobs)

    def _parse_html(self, base_url: str, html: str, max_jobs: int) -> list[JobCandidate]:
        """Parse Jobvite careers HTML into job candidates.

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
                    raw={"source": "jobvite"},
                )
            )
            if len(jobs) >= max_jobs:
                break

        return jobs

    @classmethod
    def _is_posting_href(cls, href: str | None) -> bool:
        """Report whether an href points at a Jobvite posting.

        Jobvite posting URLs carry a *singular* ``job`` path segment immediately
        followed by a terminal alphanumeric ``{jobId}`` segment
        (``/{company}/job/{jobId}``). This excludes the plural ``/{company}/jobs``
        list page and the application step (``/job/{jobId}/apply``), whose id
        segment is not terminal.

        Args:
            href: Candidate href value.

        Returns:
            True when the URL exposes a terminal singular ``job/{jobId}`` pair.
        """

        return cls._extract_external_id(href) is not None

    @staticmethod
    def _extract_external_id(job_url: str | None) -> str | None:
        """Extract the posting job id from a Jobvite URL.

        Args:
            job_url: Jobvite job URL or href.

        Returns:
            Alphanumeric job id string when the terminal singular ``job/{jobId}``
            shape is present.
        """

        if not job_url:
            return None
        parts = [part for part in urlparse(job_url).path.split("/") if part]
        for index, part in enumerate(parts):
            if part != "job" or index + 1 >= len(parts):
                continue
            candidate = parts[index + 1]
            if _JOB_ID_SEGMENT.match(candidate) and index + 2 == len(parts):
                return candidate
        return None

    @staticmethod
    def _extract_location(anchor: object) -> str | None:
        """Resolve a posting location from an anchor's surrounding markup.

        Jobvite groups a posting's metadata (department, location) alongside the
        title anchor. The location is looked up within the anchor's nearest
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

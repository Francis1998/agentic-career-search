"""Recruitee public careers site adapter.

Recruitee (``{company}.recruitee.com``) is a widely adopted applicant tracking
system. Its public careers site renders each posting as an anchor whose href
follows the ``/o/{slug}`` shape, where ``slug`` is the offer's stable,
human-readable identifier (a lowercase, hyphenated token). This adapter targets
that structure with a primary CSS selector and a resilient fallback that
recognises posting anchors purely by their URL shape, mirroring the greenhouse,
lever, ashby, and workable adapters.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from autoapply_agent.adapters.base import CareerSourceAdapter, JobCandidate, company_from_url

_SLUG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")


class RecruiteeAdapter(CareerSourceAdapter):
    """Fetch jobs from public Recruitee careers site pages."""

    adapter_name = "recruitee"

    def __init__(self, user_agent: str) -> None:
        """Create adapter instance.

        Args:
            user_agent: HTTP user agent string.
        """

        self._user_agent = user_agent

    async def fetch_jobs(
        self, base_url: str, timeout_seconds: float, max_jobs: int
    ) -> list[JobCandidate]:
        """Fetch and parse Recruitee jobs.

        Args:
            base_url: Recruitee careers site URL.
            timeout_seconds: Request timeout in seconds.
            max_jobs: Maximum number of jobs.

        Returns:
            Parsed job candidates.
        """

        html = await self._request_html(base_url, timeout_seconds, self._user_agent)
        return self._parse_html(base_url, html, max_jobs)

    def _parse_html(self, base_url: str, html: str, max_jobs: int) -> list[JobCandidate]:
        """Parse Recruitee careers HTML into job candidates.

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
                    raw={"source": "recruitee"},
                )
            )
            if len(jobs) >= max_jobs:
                break

        return jobs

    @classmethod
    def _is_posting_href(cls, href: str | None) -> bool:
        """Report whether an href points at a Recruitee posting.

        Recruitee posting URLs carry an ``/o/{slug}`` path segment pair, where
        ``slug`` is a lowercase, hyphenated identifier. Careers-site navigation
        links (about, teams, external redirects) never match that shape.

        Args:
            href: Candidate href value.

        Returns:
            True when the URL exposes an ``/o/{slug}`` segment pair.
        """

        return cls._extract_external_id(href) is not None

    @staticmethod
    def _extract_external_id(job_url: str | None) -> str | None:
        """Extract the posting slug from a Recruitee URL.

        Args:
            job_url: Recruitee job URL or href.

        Returns:
            Slug string when the ``/o/{slug}`` shape is present.
        """

        if not job_url:
            return None
        parts = [part for part in urlparse(job_url).path.split("/") if part]
        for index, part in enumerate(parts[:-1]):
            if part == "o":
                candidate = parts[index + 1]
                if _SLUG_PATTERN.match(candidate):
                    return candidate
        return None

    @staticmethod
    def _extract_location(anchor: object) -> str | None:
        """Resolve a posting location from an anchor's surrounding markup.

        Recruitee groups a posting's metadata (department, location) alongside
        the title anchor. The location is looked up within the anchor's nearest
        posting container so a posting without its own location does not inherit
        a sibling's location.

        Args:
            anchor: BeautifulSoup anchor element for the posting.

        Returns:
            Location text when discoverable, else None.
        """

        find_parent = getattr(anchor, "find_parent", None)
        if find_parent is None:
            return None
        container = find_parent(attrs={"class": re.compile("offer|job|opening", re.IGNORECASE)})
        scope = container if container is not None else getattr(anchor, "parent", None)
        if scope is None:
            return None
        select_one = getattr(scope, "select_one", None)
        if select_one is None:
            return None
        location_node = select_one("[class*=location]")
        if location_node is None:
            return None
        text = location_node.get_text(" ", strip=True)
        return text or None

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

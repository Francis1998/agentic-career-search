"""Workable public job board adapter.

Workable (``apply.workable.com/{company}``) is a widely adopted applicant
tracking system. Its public board renders each posting as an anchor whose href
follows the ``/{company}/j/{shortcode}`` shape, where ``shortcode`` is the
posting's stable identifier (an uppercase alphanumeric token). This adapter
targets that structure with a primary CSS selector and a resilient fallback
that recognises posting anchors purely by their URL shape, mirroring the
greenhouse, lever, and ashby adapters.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from autoapply_agent.adapters.base import CareerSourceAdapter, JobCandidate, company_from_url

_SHORTCODE_PATTERN = re.compile(r"^[0-9A-Z]{6,}$")


class WorkableAdapter(CareerSourceAdapter):
    """Fetch jobs from public Workable job board pages."""

    adapter_name = "workable"

    def __init__(self, user_agent: str) -> None:
        """Create adapter instance.

        Args:
            user_agent: HTTP user agent string.
        """

        self._user_agent = user_agent

    async def fetch_jobs(
        self, base_url: str, timeout_seconds: float, max_jobs: int
    ) -> list[JobCandidate]:
        """Fetch and parse Workable jobs.

        Args:
            base_url: Workable board URL.
            timeout_seconds: Request timeout in seconds.
            max_jobs: Maximum number of jobs.

        Returns:
            Parsed job candidates.
        """

        html = await self._request_html(base_url, timeout_seconds, self._user_agent)
        return self._parse_html(base_url, html, max_jobs)

    def _parse_html(self, base_url: str, html: str, max_jobs: int) -> list[JobCandidate]:
        """Parse Workable board HTML into job candidates.

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
                    raw={"source": "workable"},
                )
            )
            if len(jobs) >= max_jobs:
                break

        return jobs

    @classmethod
    def _is_posting_href(cls, href: str | None) -> bool:
        """Report whether an href points at a Workable posting.

        Workable posting URLs carry a ``/j/{shortcode}`` path segment pair,
        where ``shortcode`` is an uppercase alphanumeric identifier. Board
        navigation links (about, departments, external redirects) never match
        that shape.

        Args:
            href: Candidate href value.

        Returns:
            True when the URL exposes a ``/j/{shortcode}`` segment pair.
        """

        return cls._extract_external_id(href) is not None

    @staticmethod
    def _extract_external_id(job_url: str | None) -> str | None:
        """Extract the posting shortcode from a Workable URL.

        Args:
            job_url: Workable job URL or href.

        Returns:
            Shortcode string when the ``/j/{shortcode}`` shape is present.
        """

        if not job_url:
            return None
        parts = [part for part in urlparse(job_url).path.split("/") if part]
        for index, part in enumerate(parts[:-1]):
            if part == "j":
                candidate = parts[index + 1]
                if _SHORTCODE_PATTERN.match(candidate):
                    return candidate
        return None

    @staticmethod
    def _extract_location(anchor: object) -> str | None:
        """Resolve a posting location from an anchor's surrounding markup.

        Workable groups a posting's metadata (department, location) alongside
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
        container = find_parent(attrs={"class": re.compile("posting|job|opening", re.IGNORECASE)})
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

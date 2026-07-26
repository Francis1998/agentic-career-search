"""Breezy HR public careers site adapter.

Breezy HR (``{company}.breezy.hr``) is a widely adopted applicant tracking
system for startups and SMBs. Its public careers site renders each posting as
an anchor whose href follows the ``/p/{positionId}`` shape (an optional
hyphenated title slug may trail the id), where ``positionId`` is the posting's
stable alphanumeric identifier (commonly a 12-character hex token such as
``8f092b537498``). Application steps (``/p/{positionId}/apply``) and board
navigation links are excluded. This adapter targets that structure with a
resilient URL-shape matcher, mirroring the greenhouse, lever, ashby, workable,
recruitee, smartrecruiters, teamtailor, personio, and jobvite adapters.
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

# Breezy position ids are alphanumeric (often lowercase hex); require a minimum
# length so short path words are not mistaken for a posting id. An optional
# hyphenated title slug may trail the id (casing is not significant).
_POSITION_ID_SEGMENT = re.compile(r"^([A-Za-z0-9]{6,})(?:-[A-Za-z0-9-]+)?$")
_CONTAINER_CLASS_PATTERN = re.compile("position|job|posting|opening", re.IGNORECASE)


class BreezyHrAdapter(CareerSourceAdapter):
    """Fetch jobs from public Breezy HR careers site pages."""

    adapter_name = "breezyhr"

    def __init__(self, user_agent: str) -> None:
        """Create adapter instance.

        Args:
            user_agent: HTTP user agent string.
        """

        self._user_agent = user_agent

    async def fetch_jobs(
        self, base_url: str, timeout_seconds: float, max_jobs: int
    ) -> list[JobCandidate]:
        """Fetch and parse Breezy HR jobs.

        Args:
            base_url: Breezy HR careers site URL.
            timeout_seconds: Request timeout in seconds.
            max_jobs: Maximum number of jobs.

        Returns:
            Parsed job candidates.
        """

        html = await self._request_html(base_url, timeout_seconds, self._user_agent)
        return self._parse_html(base_url, html, max_jobs)

    def _parse_html(self, base_url: str, html: str, max_jobs: int) -> list[JobCandidate]:
        """Parse Breezy HR careers HTML into job candidates.

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
            title = self._anchor_title(anchor)
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
                    raw={"source": "breezyhr"},
                )
            )
            if len(jobs) >= max_jobs:
                break

        return jobs

    @classmethod
    def _is_posting_href(cls, href: str | None) -> bool:
        """Report whether an href points at a Breezy HR posting.

        Breezy posting URLs carry a ``p`` path segment immediately followed by a
        ``{positionId}`` segment (``/p/{positionId}``), which must be the
        terminal path segment. This excludes the application step
        (``/p/{positionId}/apply``), whose id segment is not terminal, and board
        navigation links that never match that shape.

        Args:
            href: Candidate href value.

        Returns:
            True when the URL exposes a terminal ``p/{positionId}`` segment pair.
        """

        return cls._extract_external_id(href) is not None

    @staticmethod
    def _extract_external_id(job_url: str | None) -> str | None:
        """Extract the position id from a Breezy HR URL.

        Args:
            job_url: Breezy HR job URL or href.

        Returns:
            Position id string when the terminal ``p/{positionId}`` shape is
            present.
        """

        if not job_url:
            return None
        parts = [part for part in urlparse(job_url).path.split("/") if part]
        for index, part in enumerate(parts):
            if part != "p" or index + 1 >= len(parts):
                continue
            match = _POSITION_ID_SEGMENT.match(parts[index + 1])
            if match and index + 2 == len(parts):
                return match.group(1)
        return None

    @classmethod
    def _anchor_title(cls, anchor: object) -> str | None:
        """Resolve a posting title from a Breezy HR anchor.

        Prefers visible anchor text and falls back to the ``title`` attribute
        when the link is icon-only (mirrors iCIMS/Jobvite).

        Args:
            anchor: BeautifulSoup anchor element for the posting.

        Returns:
            Title string when discoverable, else None.
        """

        get_text = getattr(anchor, "get_text", None)
        if callable(get_text):
            text = get_text(" ", strip=True)
            if isinstance(text, str) and text.strip():
                return text.strip()
        get = getattr(anchor, "get", None)
        if get is not None:
            attr_title = get("title")
            if isinstance(attr_title, str) and attr_title.strip():
                return attr_title.strip()
        return None

    @staticmethod
    def _extract_location(anchor: object) -> str | None:
        """Resolve a posting location from an anchor's surrounding markup.

        Breezy groups a posting's metadata (department, location) alongside the
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

"""Rippling public careers site adapter.

Rippling-hosted public boards commonly expose listings at
``ats.rippling.com/{company}/jobs`` and job detail pages at
``ats.rippling.com/{company}/jobs/{uuid}``. This adapter recognises terminal
``/jobs/{uuid}`` posting anchors on Rippling domains, while also accepting
relative links from branded boards.
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

_UUID_SEGMENT = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
_CONTAINER_CLASS_PATTERN = re.compile("job|position|posting|opening|role", re.IGNORECASE)
_RIPPLING_ROOT_HOST = "rippling.com"


class RipplingAdapter(CareerSourceAdapter):
    """Fetch jobs from public Rippling careers site pages."""

    adapter_name = "rippling"

    def __init__(self, user_agent: str) -> None:
        """Create adapter instance.

        Args:
            user_agent: HTTP user agent string.
        """

        self._user_agent = user_agent

    async def fetch_jobs(
        self, base_url: str, timeout_seconds: float, max_jobs: int
    ) -> list[JobCandidate]:
        """Fetch and parse Rippling jobs.

        Args:
            base_url: Rippling careers site URL.
            timeout_seconds: Request timeout in seconds.
            max_jobs: Maximum number of jobs.

        Returns:
            Parsed job candidates.
        """

        html = await self._request_html(base_url, timeout_seconds, self._user_agent)
        return self._parse_html(base_url, html, max_jobs)

    def _parse_html(self, base_url: str, html: str, max_jobs: int) -> list[JobCandidate]:
        """Parse Rippling careers HTML into job candidates.

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
                    raw={"source": "rippling"},
                )
            )
            if len(jobs) >= max_jobs:
                break

        return jobs

    @classmethod
    def _is_posting_href(cls, href: str | None) -> bool:
        """Report whether an href points at a Rippling posting.

        Args:
            href: Candidate href value.

        Returns:
            True when the URL exposes a terminal ``jobs/{uuid}`` segment pair on
            a Rippling domain, or as a relative path from a Rippling board.
        """

        return cls._extract_external_id(href) is not None

    @classmethod
    def _extract_external_id(cls, job_url: str | None) -> str | None:
        """Extract the posting id from a Rippling URL.

        Args:
            job_url: Rippling job URL or href.

        Returns:
            Job UUID string when the terminal ``/jobs/{uuid}`` shape is present.
        """

        if not job_url:
            return None

        parsed = urlparse(job_url)
        if parsed.hostname and not cls._is_rippling_host(parsed.hostname):
            return None

        parts = [part for part in parsed.path.split("/") if part]
        for index, part in enumerate(parts):
            if part != "jobs" or index + 1 >= len(parts):
                continue
            candidate = parts[index + 1]
            if _UUID_SEGMENT.match(candidate) and index + 2 == len(parts):
                return candidate
        return None

    @staticmethod
    def _is_rippling_host(hostname: str) -> bool:
        """Report whether a hostname belongs to Rippling's public web estate."""

        normalized = hostname.lower().removeprefix("www.")
        return normalized == _RIPPLING_ROOT_HOST or normalized.endswith(f".{_RIPPLING_ROOT_HOST}")

    @classmethod
    def _anchor_title(cls, anchor: object) -> str | None:
        """Resolve a posting title from a Rippling anchor."""

        get_text = getattr(anchor, "get_text", None)
        if callable(get_text):
            text = get_text(" ", strip=True)
            if isinstance(text, str) and text.strip():
                return text.strip()
        get = getattr(anchor, "get", None)
        if get is not None:
            for attr_name in ("title", "aria-label", "data-title"):
                attr_title = get(attr_name)
                if isinstance(attr_title, str) and attr_title.strip():
                    return attr_title.strip()
        return None

    @staticmethod
    def _extract_location(anchor: object) -> str | None:
        """Resolve a posting location from an anchor's surrounding markup."""

        return find_location_text(anchor, _CONTAINER_CLASS_PATTERN)

    @staticmethod
    def _normalize_href(href_value: str | Sequence[str] | None) -> str | None:
        """Normalize BeautifulSoup href values to a single URL string."""

        if isinstance(href_value, str):
            return href_value
        if isinstance(href_value, Sequence):
            for item in href_value:
                if isinstance(item, str) and item:
                    return item
        return None

"""Freshteam public careers site adapter.

Freshteam (Freshworks) hosts public careers boards at
``{company}.freshteam.com/jobs``. Listing pages render each posting as an
anchor whose href follows the ``/jobs/{jobId}/{slug}`` shape, where ``jobId`` is
a stable mixed-case token that may contain ``-`` / ``_`` characters (for
example ``aQOc95c23C-j``). This adapter recognises those posting URLs while
excluding the board index, apply/login steps, and navigation links.
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

_JOB_ID_SEGMENT = re.compile(r"^[A-Za-z0-9_-]{6,64}$")
_CONTAINER_CLASS_PATTERN = re.compile("job|position|posting|opening|role", re.IGNORECASE)
_NON_POSTING_TERMINALS = frozenset({"apply", "application", "login", "signin", "sign-in"})


class FreshteamAdapter(CareerSourceAdapter):
    """Fetch jobs from public Freshteam careers site pages."""

    adapter_name = "freshteam"

    def __init__(self, user_agent: str) -> None:
        """Create adapter instance.

        Args:
            user_agent: HTTP user agent string.
        """

        self._user_agent = user_agent

    async def fetch_jobs(
        self, base_url: str, timeout_seconds: float, max_jobs: int
    ) -> list[JobCandidate]:
        """Fetch and parse Freshteam jobs.

        Args:
            base_url: Freshteam careers site URL.
            timeout_seconds: Request timeout in seconds.
            max_jobs: Maximum number of jobs.

        Returns:
            Parsed job candidates.
        """

        html = await self._request_html(base_url, timeout_seconds, self._user_agent)
        return self._parse_html(base_url, html, max_jobs)

    def _parse_html(self, base_url: str, html: str, max_jobs: int) -> list[JobCandidate]:
        """Parse Freshteam careers HTML into job candidates.

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
                    raw={"source": "freshteam"},
                )
            )
            if len(jobs) >= max_jobs:
                break

        return jobs

    @classmethod
    def _is_posting_href(cls, href: str | None) -> bool:
        """Report whether an href points at a Freshteam posting.

        Args:
            href: Candidate href value.

        Returns:
            True when the URL exposes a ``jobs/{jobId}`` pair, optionally
            followed by one terminal title slug.
        """

        return cls._extract_external_id(href) is not None

    @staticmethod
    def _extract_external_id(job_url: str | None) -> str | None:
        """Extract the posting id from a Freshteam URL.

        Args:
            job_url: Freshteam job URL or href.

        Returns:
            Job id string when the ``/jobs/{jobId}`` detail shape is present.
        """

        if not job_url:
            return None
        parts = [part for part in urlparse(job_url).path.split("/") if part]
        for index, part in enumerate(parts):
            if part != "jobs" or index + 1 >= len(parts):
                continue
            candidate = parts[index + 1]
            if not _JOB_ID_SEGMENT.match(candidate):
                continue
            if index + 2 == len(parts):
                return candidate
            terminal = parts[index + 2].lower()
            if index + 3 == len(parts) and terminal not in _NON_POSTING_TERMINALS:
                return candidate
        return None

    @classmethod
    def _anchor_title(cls, anchor: object) -> str | None:
        """Resolve a posting title from a Freshteam anchor."""

        get_text = getattr(anchor, "get_text", None)
        if callable(get_text):
            text = get_text(" ", strip=True)
            if isinstance(text, str) and text.strip():
                return text.strip()
        get = getattr(anchor, "get", None)
        if get is not None:
            for attr_name in ("title", "aria-label", "data-portal-title"):
                attr_title = get(attr_name)
                if isinstance(attr_title, str) and attr_title.strip():
                    return attr_title.strip()
        return None

    @staticmethod
    def _extract_location(anchor: object) -> str | None:
        """Resolve a posting location from Freshteam anchor metadata or markup."""

        get = getattr(anchor, "get", None)
        if get is not None:
            attr_location = get("data-portal-location")
            if isinstance(attr_location, str) and attr_location.strip():
                return attr_location.strip()
            remote_value = get("data-portal-remote-location")
            if isinstance(remote_value, str) and remote_value.lower() == "true":
                return "Remote"
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

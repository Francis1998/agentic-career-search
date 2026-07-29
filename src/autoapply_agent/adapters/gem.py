"""Gem public careers site adapter.

Gem (``jobs.gem.com`` / ``{company}.gem.com``) hosts public careers boards whose
listing pages render each posting as an anchor. Detail hrefs commonly follow
``/{company}/{jobId}`` on ``jobs.gem.com``, ``/jobs/{jobId}`` or
``/openings/{id}``, or ``/careers/...`` on tenant subdomains. This adapter
recognises those posting URLs while excluding the board index, apply/login
steps, and navigation links.
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

_JOB_ID_SEGMENT = re.compile(r"^[A-Za-z0-9_-]{2,128}$")
_CONTAINER_CLASS_PATTERN = re.compile("job|position|posting|opening|role", re.IGNORECASE)
_NON_POSTING_TERMINALS = frozenset({"apply", "application", "login", "signin", "sign-in", "about"})
_DETAIL_PREFIXES = frozenset({"jobs", "openings"})


class GemAdapter(CareerSourceAdapter):
    """Fetch jobs from public Gem careers site pages."""

    adapter_name = "gem"

    def __init__(self, user_agent: str) -> None:
        """Create adapter instance.

        Args:
            user_agent: HTTP user agent string.
        """

        self._user_agent = user_agent

    async def fetch_jobs(
        self, base_url: str, timeout_seconds: float, max_jobs: int
    ) -> list[JobCandidate]:
        """Fetch and parse Gem jobs.

        Args:
            base_url: Gem careers site URL.
            timeout_seconds: Request timeout in seconds.
            max_jobs: Maximum number of jobs.

        Returns:
            Parsed job candidates.
        """

        html = await self._request_html(base_url, timeout_seconds, self._user_agent)
        return self._parse_html(base_url, html, max_jobs)

    def _parse_html(self, base_url: str, html: str, max_jobs: int) -> list[JobCandidate]:
        """Parse Gem careers HTML into job candidates.

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
                    raw={"source": "gem"},
                )
            )
            if len(jobs) >= max_jobs:
                break

        return jobs

    @classmethod
    def _is_posting_href(cls, href: str | None) -> bool:
        """Report whether an href points at a Gem posting.

        Args:
            href: Candidate href value.

        Returns:
            True when the URL exposes a recognised Gem job detail shape.
        """

        return cls._extract_external_id(href) is not None

    @classmethod
    def _extract_external_id(cls, job_url: str | None) -> str | None:
        """Extract the posting id from a Gem URL.

        Args:
            job_url: Gem job URL or href.

        Returns:
            Job post id when a recognised detail shape is present.
        """

        if not job_url:
            return None

        parsed = urlparse(job_url)
        parts = [part for part in parsed.path.split("/") if part]
        host = (parsed.hostname or "").lower()

        careers_index = next(
            (index for index, part in enumerate(parts) if part == "careers"),
            None,
        )
        if careers_index is not None:
            remainder = parts[careers_index + 1 :]
            if len(remainder) == 1:
                candidate = remainder[0]
                if cls._is_job_id(candidate):
                    return candidate
            if len(remainder) >= 2 and remainder[0] in _DETAIL_PREFIXES:
                candidate = remainder[1]
                if cls._accepts_detail_candidate(remainder, 1, candidate):
                    return candidate

        if host in {"jobs.gem.com", "www.jobs.gem.com"}:
            if len(parts) == 3 and parts[2].lower() in _NON_POSTING_TERMINALS:
                return None

        if len(parts) == 2 and parts[0] not in _DETAIL_PREFIXES and parts[0] != "careers":
            candidate = parts[1]
            if cls._accepts_detail_candidate(parts, 1, candidate):
                return candidate

        for index, part in enumerate(parts):
            if part not in _DETAIL_PREFIXES or index + 1 >= len(parts):
                continue
            candidate = parts[index + 1]
            if cls._accepts_detail_candidate(parts, index + 1, candidate):
                return candidate

        return None

    @classmethod
    def _accepts_detail_candidate(
        cls, parts: list[str], candidate_index: int, candidate: str
    ) -> bool:
        """Report whether a path segment is a valid Gem posting id."""

        if not cls._is_job_id(candidate):
            return False
        if candidate_index + 1 == len(parts):
            return True
        return parts[candidate_index + 1].lower() not in _NON_POSTING_TERMINALS

    @staticmethod
    def _is_job_id(candidate: str) -> bool:
        """Report whether a path segment looks like a Gem job post id."""

        return bool(_JOB_ID_SEGMENT.match(candidate)) and candidate.lower() not in (
            _NON_POSTING_TERMINALS
        )

    @classmethod
    def _anchor_title(cls, anchor: object) -> str | None:
        """Resolve a posting title from a Gem anchor."""

        get_text = getattr(anchor, "get_text", None)
        if callable(get_text):
            text = get_text(" ", strip=True)
            if isinstance(text, str) and text.strip():
                return text.strip()
        get = getattr(anchor, "get", None)
        if get is not None:
            for attr_name in ("title", "aria-label", "data-job-title"):
                attr_title = get(attr_name)
                if isinstance(attr_title, str) and attr_title.strip():
                    return attr_title.strip()
        return None

    @staticmethod
    def _extract_location(anchor: object) -> str | None:
        """Resolve a posting location from Gem anchor metadata or markup."""

        get = getattr(anchor, "get", None)
        if get is not None:
            for attr_name in ("data-location", "data-job-location"):
                attr_location = get(attr_name)
                if isinstance(attr_location, str) and attr_location.strip():
                    return attr_location.strip()
            remote_value = get("data-remote")
            if isinstance(remote_value, str) and remote_value.lower() in {"true", "1", "yes"}:
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

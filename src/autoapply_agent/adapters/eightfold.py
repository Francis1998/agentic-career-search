"""Eightfold AI public careers site adapter.

Eightfold (``{company}.eightfold.ai`` and branded careers pages) hosts public
boards whose listing pages render each posting as an anchor. Detail hrefs
commonly follow ``/careers/job/{id}``, ``/careers/job/{id}/{slug}``,
``/career_detail/{id}``, ``/position/{id}``, or ``/jobs/{id}``. This adapter
recognises those posting URLs while excluding the board index, apply/login
steps, search facets, and navigation links.
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
_CONTAINER_CLASS_PATTERN = re.compile("job|position|posting|opening|role|career", re.IGNORECASE)
_NON_POSTING_TERMINALS = frozenset(
    {"apply", "application", "login", "signin", "sign-in", "about", "search", "facet", "facets"}
)
_DETAIL_PREFIXES = frozenset({"career_detail", "position", "jobs"})


class EightfoldAdapter(CareerSourceAdapter):
    """Fetch jobs from public Eightfold careers site pages."""

    adapter_name = "eightfold"

    def __init__(self, user_agent: str) -> None:
        """Create adapter instance.

        Args:
            user_agent: HTTP user agent string.
        """

        self._user_agent = user_agent

    async def fetch_jobs(
        self, base_url: str, timeout_seconds: float, max_jobs: int
    ) -> list[JobCandidate]:
        """Fetch and parse Eightfold jobs.

        Args:
            base_url: Eightfold careers site URL.
            timeout_seconds: Request timeout in seconds.
            max_jobs: Maximum number of jobs.

        Returns:
            Parsed job candidates.
        """

        html = await self._request_html(base_url, timeout_seconds, self._user_agent)
        return self._parse_html(base_url, html, max_jobs)

    def _parse_html(self, base_url: str, html: str, max_jobs: int) -> list[JobCandidate]:
        """Parse Eightfold careers HTML into job candidates.

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
                    raw={"source": "eightfold"},
                )
            )
            if len(jobs) >= max_jobs:
                break

        return jobs

    @classmethod
    def _is_posting_href(cls, href: str | None) -> bool:
        """Report whether an href points at an Eightfold posting.

        Args:
            href: Candidate href value.

        Returns:
            True when the URL exposes a recognised Eightfold job detail shape.
        """

        return cls._extract_external_id(href) is not None

    @classmethod
    def _extract_external_id(cls, job_url: str | None) -> str | None:
        """Extract the posting id from an Eightfold URL.

        Args:
            job_url: Eightfold job URL or href.

        Returns:
            Job post id when a recognised detail shape is present.
        """

        if not job_url:
            return None

        parsed = urlparse(job_url)
        parts = [part for part in parsed.path.split("/") if part]
        if not parts:
            return None

        lowered = [part.lower() for part in parts]
        if any(part in _NON_POSTING_TERMINALS for part in lowered):
            return None

        careers_index = next(
            (index for index, part in enumerate(lowered) if part == "careers"),
            None,
        )
        if careers_index is not None:
            remainder = parts[careers_index + 1 :]
            remainder_lowered = lowered[careers_index + 1 :]
            if not remainder:
                return None
            if remainder_lowered[0] == "job" and len(remainder) >= 2:
                candidate = remainder[1]
                if cls._accepts_careers_job_candidate(remainder, 1, candidate):
                    return candidate
            return None

        for index, part in enumerate(lowered):
            if part not in _DETAIL_PREFIXES or index + 1 >= len(parts):
                continue
            candidate = parts[index + 1]
            if cls._accepts_detail_candidate(parts, index + 1, candidate):
                return candidate

        return None

    @classmethod
    def _accepts_careers_job_candidate(
        cls, remainder: list[str], candidate_index: int, candidate: str
    ) -> bool:
        """Report whether a ``/careers/job/{id}`` segment is a valid posting id."""

        if not cls._is_job_id(candidate):
            return False
        if candidate_index + 1 == len(remainder):
            return True
        # Optional slug after the id is accepted; further apply/login segments are not.
        if candidate_index + 2 == len(remainder):
            return remainder[candidate_index + 1].lower() not in _NON_POSTING_TERMINALS
        return False

    @classmethod
    def _accepts_detail_candidate(
        cls, parts: list[str], candidate_index: int, candidate: str
    ) -> bool:
        """Report whether a path segment is a valid Eightfold posting id."""

        if not cls._is_job_id(candidate):
            return False
        if candidate_index + 1 == len(parts):
            return True
        return parts[candidate_index + 1].lower() not in _NON_POSTING_TERMINALS

    @staticmethod
    def _is_job_id(candidate: str) -> bool:
        """Report whether a path segment looks like an Eightfold job post id."""

        return bool(_JOB_ID_SEGMENT.match(candidate)) and candidate.lower() not in (
            _NON_POSTING_TERMINALS
        )

    @classmethod
    def _anchor_title(cls, anchor: object) -> str | None:
        """Resolve a posting title from an Eightfold anchor."""

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
        """Resolve a posting location from Eightfold anchor metadata or markup."""

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

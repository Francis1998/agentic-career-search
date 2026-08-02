"""Join public careers site adapter.

Join-hosted public careers boards expose listing pages whose postings render as
anchors. Detail hrefs commonly follow ``/companies/{slug}/jobs/{id}``,
``/jobs/{id}``, ``/job/{id}``, and ``/positions/{id}``. This adapter recognises
those posting URLs while excluding board indexes plus apply/login/about links.
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

_JOB_ID_SEGMENT = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
_CONTAINER_CLASS_PATTERN = re.compile("job|position|posting|opening|role", re.IGNORECASE)
_NON_POSTING_TERMINALS = frozenset(
    {
        "apply",
        "application",
        "login",
        "signin",
        "sign-in",
        "about",
    }
)
_JOBS_PREFIX = "jobs"
_JOB_PREFIX = "job"
_POSITIONS_PREFIX = "positions"
_COMPANIES_PREFIX = "companies"


class JoinAdapter(CareerSourceAdapter):
    """Fetch jobs from public Join careers site pages."""

    adapter_name = "join"

    def __init__(self, user_agent: str) -> None:
        """Create adapter instance.

        Args:
            user_agent: HTTP user agent string.
        """

        self._user_agent = user_agent

    async def fetch_jobs(
        self, base_url: str, timeout_seconds: float, max_jobs: int
    ) -> list[JobCandidate]:
        """Fetch and parse Join jobs.

        Args:
            base_url: Join careers site URL.
            timeout_seconds: Request timeout in seconds.
            max_jobs: Maximum number of jobs.

        Returns:
            Parsed job candidates.
        """

        html = await self._request_html(base_url, timeout_seconds, self._user_agent)
        return self._parse_html(base_url, html, max_jobs)

    def _parse_html(self, base_url: str, html: str, max_jobs: int) -> list[JobCandidate]:
        """Parse Join careers HTML into job candidates.

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
                    raw={"source": "join"},
                )
            )
            if len(jobs) >= max_jobs:
                break

        return jobs

    @classmethod
    def _is_posting_href(cls, href: str | None) -> bool:
        """Report whether an href points at a Join posting.

        Args:
            href: Candidate href value.

        Returns:
            True when the URL exposes a recognised Join job detail shape.
        """

        return cls._extract_external_id(href) is not None

    @classmethod
    def _extract_external_id(cls, job_url: str | None) -> str | None:
        """Extract the posting id from a Join URL.

        Args:
            job_url: Join job URL or href.

        Returns:
            Job post id when a recognised detail shape is present.
        """

        if not job_url:
            return None

        parts = [part for part in urlparse(job_url).path.split("/") if part]
        lowered = [part.lower() for part in parts]

        if parts and lowered[-1] in _NON_POSTING_TERMINALS:
            return None

        for index, part in enumerate(lowered):
            if (
                part == _COMPANIES_PREFIX
                and index + 3 < len(parts)
                and lowered[index + 2] == _JOBS_PREFIX
            ):
                candidate = parts[index + 3]
                if cls._accepts_detail_candidate(lowered, index + 3, candidate):
                    return candidate

            if part == _JOBS_PREFIX and index + 1 < len(parts):
                candidate = parts[index + 1]
                if cls._accepts_detail_candidate(lowered, index + 1, candidate):
                    return candidate

            if part == _JOB_PREFIX and index + 1 < len(parts):
                candidate = parts[index + 1]
                if cls._accepts_detail_candidate(lowered, index + 1, candidate):
                    return candidate

            if part == _POSITIONS_PREFIX and index + 1 < len(parts):
                candidate = parts[index + 1]
                if cls._accepts_detail_candidate(lowered, index + 1, candidate):
                    return candidate

        return None

    @classmethod
    def _accepts_detail_candidate(
        cls, lowered_parts: list[str], candidate_index: int, candidate: str
    ) -> bool:
        """Report whether a path segment is a valid Join posting id."""

        if not cls._is_job_id(candidate):
            return False
        if candidate_index + 1 == len(lowered_parts):
            return True
        return lowered_parts[candidate_index + 1] not in _NON_POSTING_TERMINALS

    @staticmethod
    def _is_job_id(candidate: str) -> bool:
        """Report whether a path segment looks like a Join job post id."""

        if candidate.lower() in _NON_POSTING_TERMINALS:
            return False
        if candidate.lower() in {
            _JOBS_PREFIX,
            _JOB_PREFIX,
            _POSITIONS_PREFIX,
            _COMPANIES_PREFIX,
        }:
            return False
        return bool(_JOB_ID_SEGMENT.match(candidate))

    @classmethod
    def _anchor_title(cls, anchor: object) -> str | None:
        """Resolve a posting title from a Join anchor."""

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
        """Resolve a posting location from Join anchor metadata or markup."""

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

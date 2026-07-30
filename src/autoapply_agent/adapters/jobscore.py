"""JobScore public careers site adapter.

JobScore (``careers.jobscore.com`` / ``{company}.jobscore.com``) hosts public
careers boards whose listing pages render each posting as an anchor. Detail
hrefs commonly follow ``/careers/{company}/jobs/{slug}-{id}`` or
``/careers/{company}/jobs/{id}``, ``/jobs/{id}`` or ``/jobs/{slug}/{id}``, and
``/position/{id}`` or ``/positions/{id}``. This adapter recognises those posting
URLs while excluding the board index, apply/login steps, and navigation links.
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
_SLUG_ID_SEGMENT = re.compile(r"^(?P<slug>.+)-(?P<id>[A-Za-z0-9]+)$")
_CONTAINER_CLASS_PATTERN = re.compile("job|position|posting|opening|role", re.IGNORECASE)
_NON_POSTING_TERMINALS = frozenset({"apply", "application", "login", "signin", "sign-in", "about"})
_JOBS_PREFIX = "jobs"
_POSITION_PREFIXES = frozenset({"position", "positions"})


class JobScoreAdapter(CareerSourceAdapter):
    """Fetch jobs from public JobScore careers site pages."""

    adapter_name = "jobscore"

    def __init__(self, user_agent: str) -> None:
        """Create adapter instance.

        Args:
            user_agent: HTTP user agent string.
        """

        self._user_agent = user_agent

    async def fetch_jobs(
        self, base_url: str, timeout_seconds: float, max_jobs: int
    ) -> list[JobCandidate]:
        """Fetch and parse JobScore jobs.

        Args:
            base_url: JobScore careers site URL.
            timeout_seconds: Request timeout in seconds.
            max_jobs: Maximum number of jobs.

        Returns:
            Parsed job candidates.
        """

        html = await self._request_html(base_url, timeout_seconds, self._user_agent)
        return self._parse_html(base_url, html, max_jobs)

    def _parse_html(self, base_url: str, html: str, max_jobs: int) -> list[JobCandidate]:
        """Parse JobScore careers HTML into job candidates.

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
                    raw={"source": "jobscore"},
                )
            )
            if len(jobs) >= max_jobs:
                break

        return jobs

    @classmethod
    def _is_posting_href(cls, href: str | None) -> bool:
        """Report whether an href points at a JobScore posting.

        Args:
            href: Candidate href value.

        Returns:
            True when the URL exposes a recognised JobScore job detail shape.
        """

        return cls._extract_external_id(href) is not None

    @classmethod
    def _extract_external_id(cls, job_url: str | None) -> str | None:
        """Extract the posting id from a JobScore URL.

        Args:
            job_url: JobScore job URL or href.

        Returns:
            Job post id when a recognised detail shape is present.
        """

        if not job_url:
            return None

        parts = [part for part in urlparse(job_url).path.split("/") if part]

        careers_index = next(
            (index for index, part in enumerate(parts) if part == "careers"),
            None,
        )
        if careers_index is not None:
            remainder = parts[careers_index + 1 :]
            # /careers/{company}/jobs/{slug}-{id} or /careers/{company}/jobs/{id}
            if len(remainder) >= 3 and remainder[1] == _JOBS_PREFIX:
                return cls._accept_jobs_tail(remainder[2:])

        for index, part in enumerate(parts):
            if part == _JOBS_PREFIX and index + 1 < len(parts):
                # Skip careers/{company}/jobs/... already handled above when
                # "careers" appears earlier; still accept bare /jobs/... shapes.
                if careers_index is not None and index > careers_index:
                    continue
                return cls._accept_jobs_tail(parts[index + 1 :])

            if part in _POSITION_PREFIXES and index + 1 < len(parts):
                candidate = parts[index + 1]
                if cls._accepts_detail_candidate(parts, index + 1, candidate):
                    return cls._coerce_detail_id(candidate)

        return None

    @classmethod
    def _accept_jobs_tail(cls, tail: list[str]) -> str | None:
        """Accept a JobScore ``jobs/...`` path tail and return its posting id.

        Recognises ``/{id}``, ``/{slug}-{id}``, and ``/{slug}/{id}`` tails while
        rejecting apply/login terminals.
        """

        if not tail:
            return None

        if len(tail) == 1:
            return cls._coerce_detail_id(tail[0]) if cls._is_job_id_segment(tail[0]) else None

        if len(tail) == 2:
            slug, candidate = tail[0], tail[1]
            if not slug or slug.lower() in _NON_POSTING_TERMINALS:
                return None
            if not cls._is_job_id(candidate):
                return None
            return candidate

        # /jobs/{id}/apply or /jobs/{slug}/{id}/apply — reject non-posting steps
        if tail[-1].lower() in _NON_POSTING_TERMINALS:
            return None
        return None

    @classmethod
    def _accepts_detail_candidate(
        cls, parts: list[str], candidate_index: int, candidate: str
    ) -> bool:
        """Report whether a path segment is a valid JobScore posting id."""

        if not cls._is_job_id(candidate):
            return False
        if candidate_index + 1 == len(parts):
            return True
        return parts[candidate_index + 1].lower() not in _NON_POSTING_TERMINALS

    @classmethod
    def _coerce_detail_id(cls, segment: str) -> str | None:
        """Resolve a bare id or ``{slug}-{id}`` segment to a posting id."""

        if not cls._is_job_id_segment(segment):
            return None
        slug_match = _SLUG_ID_SEGMENT.match(segment)
        if slug_match and re.search(r"\d", slug_match.group("id")):
            return slug_match.group("id")
        if cls._is_job_id(segment):
            return segment
        return None

    @classmethod
    def _is_job_id(cls, candidate: str) -> bool:
        """Report whether a path segment looks like a JobScore job post id."""

        return cls._is_job_id_segment(candidate) and candidate.lower() not in (
            _NON_POSTING_TERMINALS
        )

    @staticmethod
    def _is_job_id_segment(candidate: str) -> bool:
        """Report whether a path segment matches the JobScore id charset."""

        return bool(_JOB_ID_SEGMENT.match(candidate))

    @classmethod
    def _anchor_title(cls, anchor: object) -> str | None:
        """Resolve a posting title from a JobScore anchor."""

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
        """Resolve a posting location from JobScore anchor metadata or markup."""

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

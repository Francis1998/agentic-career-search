"""Zoho Recruit public careers portal adapter.

Zoho Recruit powers public careers portals commonly hosted on
``*.zohorecruit.com`` or vanity-domain proxies. Posting detail links expose a
job id via ``jobId`` / ``jid`` / ``job_id`` query parameters (for example
``/jobs/Careers?jobId=XXXX``) or via path-shaped detail pages such as
``/jobs/{id}``, ``/job/{id}``, ``/careers/{id}``, and
``/Jobs/Careers/{id}``. Application steps (``mode=apply``, ``source=apply``,
``login``, ``apply``) are excluded. This adapter mirrors the SuccessFactors/
Taleo URL-shape scrapers used for other enterprise ATS sources.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from urllib.parse import parse_qs, urljoin, urlparse

from bs4 import BeautifulSoup

from autoapply_agent.adapters.base import (
    CareerSourceAdapter,
    JobCandidate,
    company_from_url,
    find_location_text,
)

_JOB_ID_SEGMENT = re.compile(r"^[A-Za-z0-9_-]{2,64}$")
_CONTAINER_CLASS_PATTERN = re.compile("job|position|posting|opening|career", re.IGNORECASE)
_APPLY_MARKERS = frozenset({"apply", "login", "signin", "sign-in"})


class ZohoRecruitAdapter(CareerSourceAdapter):
    """Fetch jobs from public Zoho Recruit careers portals."""

    adapter_name = "zoho_recruit"

    def __init__(self, user_agent: str) -> None:
        """Create adapter instance.

        Args:
            user_agent: HTTP user agent string.
        """

        self._user_agent = user_agent

    async def fetch_jobs(
        self, base_url: str, timeout_seconds: float, max_jobs: int
    ) -> list[JobCandidate]:
        """Fetch and parse Zoho Recruit jobs.

        Args:
            base_url: Zoho Recruit careers portal URL.
            timeout_seconds: Request timeout in seconds.
            max_jobs: Maximum number of jobs.

        Returns:
            Parsed job candidates.
        """

        html = await self._request_html(base_url, timeout_seconds, self._user_agent)
        return self._parse_html(base_url, html, max_jobs)

    def _parse_html(self, base_url: str, html: str, max_jobs: int) -> list[JobCandidate]:
        """Parse Zoho Recruit careers HTML into job candidates.

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
                    raw={"source": "zoho_recruit"},
                )
            )
            if len(jobs) >= max_jobs:
                break

        return jobs

    @classmethod
    def _is_posting_href(cls, href: str | None) -> bool:
        """Report whether an href points at a Zoho Recruit posting detail page.

        Args:
            href: Candidate href value.

        Returns:
            True when a job id can be extracted and the URL is not an apply/login
            step.
        """

        return cls._extract_external_id(href) is not None

    @staticmethod
    def _extract_external_id(job_url: str | None) -> str | None:
        """Extract the job id from a Zoho Recruit careers URL.

        Recognises ``jobId`` / ``jid`` / ``job_id`` query parameters plus path
        forms ``/jobs/{id}``, ``/job/{id}``, ``/careers/{id}``, and
        ``/Jobs/Careers/{id}``. Apply/login terminals and ``source=apply`` /
        ``mode=apply`` query links are rejected.

        Args:
            job_url: Zoho Recruit job URL or href.

        Returns:
            Job id string when the posting detail shape is present.
        """

        if not job_url:
            return None
        parsed = urlparse(job_url)
        parts = [part for part in parsed.path.split("/") if part]
        if parts and parts[-1].lower() in _APPLY_MARKERS:
            return None
        query = parse_qs(parsed.query)
        if ZohoRecruitAdapter._has_apply_query(query):
            return None
        job_values = query.get("jobId") or query.get("jid") or query.get("job_id")
        if job_values:
            candidate = job_values[0].strip()
            if _JOB_ID_SEGMENT.match(candidate):
                return candidate
        lowered_parts = [part.lower() for part in parts]
        for index, part in enumerate(lowered_parts):
            if part == "jobs" and index + 1 < len(parts) and lowered_parts[index + 1] == "careers":
                if index + 2 >= len(parts):
                    continue
                candidate_index = index + 2
            elif part in {"job", "jobs", "careers"}:
                candidate_index = index + 1
            else:
                continue
            if candidate_index >= len(parts):
                continue
            candidate = parts[candidate_index]
            if _JOB_ID_SEGMENT.match(candidate) and candidate_index + 1 == len(parts):
                return candidate
        return None

    @staticmethod
    def _has_apply_query(query: dict[str, list[str]]) -> bool:
        """Report whether a parsed query string is an apply-step link.

        Args:
            query: Parsed query-string values keyed by parameter name.

        Returns:
            True when ``mode`` or ``source`` is set to ``apply``.
        """

        for key, values in query.items():
            if key.lower() not in {"mode", "source"}:
                continue
            if any(value.lower() == "apply" for value in values):
                return True
        return False

    @classmethod
    def _anchor_title(cls, anchor: object) -> str | None:
        """Resolve a posting title from a Zoho Recruit anchor.

        Prefers visible anchor text and falls back to the ``title`` attribute
        when the link is icon-only or rendered with hidden text.

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

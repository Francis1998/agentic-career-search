"""iCIMS public careers portal adapter.

iCIMS is one of the most widely deployed enterprise applicant tracking systems;
its public careers portals are hosted at ``careers-{tenant}.icims.com`` (and the
``careers.{tenant}.icims.com`` / vanity-domain proxy variants) and each posting
detail page follows the ``/jobs/{jobId}/{slug}/job`` shape, where ``jobId`` is a
numeric requisition id and the ``{slug}`` segment is optional (``/jobs/{jobId}/job``).
Note the *terminal* literal ``job`` segment, which distinguishes a posting detail
page from the ``/jobs/search`` listing grid and from the application step
(``?mode=apply`` / a terminal ``login`` segment). This adapter targets that
structure with a resilient URL-shape matcher, mirroring the greenhouse, lever,
ashby, workable, recruitee, smartrecruiters, teamtailor, personio, and jobvite
adapters. iCIMS job ids are purely numeric (unlike Jobvite's alphanumeric ids),
so a dedicated numeric matcher is used.
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

# iCIMS requisition ids are numeric path segments (e.g. ``2931``).
_JOB_ID_SEGMENT = re.compile(r"^[0-9]+$")
_CONTAINER_CLASS_PATTERN = re.compile("job|position|posting", re.IGNORECASE)


class IcimsAdapter(CareerSourceAdapter):
    """Fetch jobs from public iCIMS careers portal pages."""

    adapter_name = "icims"

    def __init__(self, user_agent: str) -> None:
        """Create adapter instance.

        Args:
            user_agent: HTTP user agent string.
        """

        self._user_agent = user_agent

    async def fetch_jobs(
        self, base_url: str, timeout_seconds: float, max_jobs: int
    ) -> list[JobCandidate]:
        """Fetch and parse iCIMS jobs.

        Args:
            base_url: iCIMS careers portal URL.
            timeout_seconds: Request timeout in seconds.
            max_jobs: Maximum number of jobs.

        Returns:
            Parsed job candidates.
        """

        html = await self._request_html(base_url, timeout_seconds, self._user_agent)
        return self._parse_html(base_url, html, max_jobs)

    def _parse_html(self, base_url: str, html: str, max_jobs: int) -> list[JobCandidate]:
        """Parse iCIMS careers HTML into job candidates.

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
                    raw={"source": "icims"},
                )
            )
            if len(jobs) >= max_jobs:
                break

        return jobs

    @classmethod
    def _is_posting_href(cls, href: str | None) -> bool:
        """Report whether an href points at an iCIMS posting detail page.

        iCIMS posting URLs carry a numeric ``{jobId}`` segment immediately after
        a ``jobs`` segment and a *terminal* literal ``job`` segment
        (``/jobs/{jobId}/{slug}/job`` or ``/jobs/{jobId}/job``). This excludes
        the ``/jobs/search`` listing grid and the application step, whose
        terminal segment is not ``job``.

        Args:
            href: Candidate href value.

        Returns:
            True when the URL exposes the terminal ``job`` detail shape.
        """

        return cls._extract_external_id(href) is not None

    @staticmethod
    def _extract_external_id(job_url: str | None) -> str | None:
        """Extract the numeric requisition id from an iCIMS URL.

        Args:
            job_url: iCIMS job URL or href.

        Returns:
            Numeric job id string when the ``jobs/{jobId}/.../job`` detail shape
            is present, else None.
        """

        if not job_url:
            return None
        parts = [part for part in urlparse(job_url).path.split("/") if part]
        if not parts or parts[-1] != "job":
            return None
        for index, part in enumerate(parts):
            if part != "jobs" or index + 1 >= len(parts):
                continue
            candidate = parts[index + 1]
            if _JOB_ID_SEGMENT.match(candidate):
                return candidate
        return None

    @classmethod
    def _anchor_title(cls, anchor: object) -> str | None:
        """Resolve a posting title from an iCIMS anchor.

        iCIMS renders the title as the anchor text but also exposes it on the
        anchor's ``title`` attribute; the attribute is preferred when the visible
        text is empty (for example an icon-only or aria-labelled link).

        Args:
            anchor: BeautifulSoup anchor element for the posting.

        Returns:
            Posting title text when discoverable, else None.
        """

        text = anchor.get_text(" ", strip=True) if hasattr(anchor, "get_text") else ""
        if text:
            return text
        get = getattr(anchor, "get", None)
        if get is not None:
            attr_title = get("title")
            if isinstance(attr_title, str) and attr_title.strip():
                return attr_title.strip()
        return None

    @staticmethod
    def _extract_location(anchor: object) -> str | None:
        """Resolve a posting location from an anchor's surrounding markup.

        iCIMS groups a posting's metadata (location, department) alongside the
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

"""Greenhouse public board adapter."""

from __future__ import annotations

from collections.abc import Sequence
from urllib.parse import parse_qs, urljoin, urlparse

from bs4 import BeautifulSoup

from autoapply_agent.adapters.base import CareerSourceAdapter, JobCandidate, company_from_url


class GreenhouseAdapter(CareerSourceAdapter):
    """Fetch jobs from public Greenhouse board pages."""

    adapter_name = "greenhouse"

    def __init__(self, user_agent: str) -> None:
        """Create adapter instance.

        Args:
            user_agent: HTTP user agent string.
        """

        self._user_agent = user_agent

    async def fetch_jobs(
        self, base_url: str, timeout_seconds: float, max_jobs: int
    ) -> list[JobCandidate]:
        """Fetch and parse Greenhouse jobs.

        Args:
            base_url: Greenhouse board URL.
            timeout_seconds: Request timeout in seconds.
            max_jobs: Maximum number of jobs.

        Returns:
            Parsed job candidates.
        """

        html = await self._request_html(base_url, timeout_seconds, self._user_agent)
        return self._parse_html(base_url, html, max_jobs)

    def _parse_html(self, base_url: str, html: str, max_jobs: int) -> list[JobCandidate]:
        """Parse Greenhouse HTML into job candidates.

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
        anchors = list(soup.select("div.opening a, section.opening a, a.opening"))
        if not anchors:
            fallback_anchors = list(soup.select("a[href]"))
            anchors = []
            for anchor in fallback_anchors:
                href = self._normalize_href(anchor.get("href"))
                if isinstance(href, str) and self._looks_like_posting_href(href):
                    anchors.append(anchor)

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

            opening_root = anchor.find_parent(class_="opening")
            location_text = None
            if opening_root is not None:
                location_node = opening_root.select_one("span.location")
                if location_node is not None:
                    location_text = location_node.get_text(" ", strip=True)

            jobs.append(
                JobCandidate(
                    external_id=self._extract_external_id(absolute_url),
                    title=title,
                    location=location_text,
                    company=company_from_url(base_url),
                    url=absolute_url,
                    raw={"source": "greenhouse"},
                )
            )
            if len(jobs) >= max_jobs:
                break

        return jobs

    @staticmethod
    def _looks_like_posting_href(href: str) -> bool:
        """Report whether a fallback anchor href points at a Greenhouse posting.

        Greenhouse posting URLs expose a ``jobs`` path segment
        (``/{board}/jobs/{id}``) or a ``gh_jid`` query parameter (embedded
        boards). Matching the bare substring ``/job`` was too loose: careers
        navigation links such as ``/job_alerts`` or ``/jobseekers/faq`` contain
        it and surfaced as phantom job candidates. Requiring a whole ``jobs``
        path segment (or the ``gh_jid`` query parameter) keeps only true
        postings.

        Args:
            href: Candidate anchor href value.

        Returns:
            True when the href exposes a ``jobs`` path segment or ``gh_jid``.
        """

        parsed = urlparse(href)
        segments = [part for part in parsed.path.split("/") if part]
        if "jobs" in segments:
            return True
        return "gh_jid" in parse_qs(parsed.query)

    @staticmethod
    def _extract_external_id(job_url: str) -> str | None:
        """Extract external ID from Greenhouse URL/query.

        Args:
            job_url: Job posting URL.

        Returns:
            Parsed external job id when present.
        """

        parsed = urlparse(job_url)
        query_map = parse_qs(parsed.query)
        for key in ("gh_jid", "jid"):
            value = query_map.get(key)
            if value:
                return value[0]

        path_parts = [part for part in parsed.path.split("/") if part]
        if path_parts:
            trailing = path_parts[-1]
            if trailing.isdigit():
                return trailing
        return None

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

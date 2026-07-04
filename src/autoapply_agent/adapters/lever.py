"""Lever public postings adapter."""

from __future__ import annotations

from collections.abc import Sequence
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from autoapply_agent.adapters.base import CareerSourceAdapter, JobCandidate, company_from_url


class LeverAdapter(CareerSourceAdapter):
    """Fetch jobs from public Lever postings pages."""

    adapter_name = "lever"

    def __init__(self, user_agent: str) -> None:
        """Create adapter instance.

        Args:
            user_agent: HTTP user agent string.
        """

        self._user_agent = user_agent

    async def fetch_jobs(
        self, base_url: str, timeout_seconds: float, max_jobs: int
    ) -> list[JobCandidate]:
        """Fetch and parse Lever jobs.

        Args:
            base_url: Lever source URL.
            timeout_seconds: Request timeout in seconds.
            max_jobs: Maximum number of jobs.

        Returns:
            Parsed job candidates.
        """

        html = await self._request_html(base_url, timeout_seconds, self._user_agent)
        return self._parse_html(base_url, html, max_jobs)

    def _parse_html(self, base_url: str, html: str, max_jobs: int) -> list[JobCandidate]:
        """Parse Lever postings HTML.

        Args:
            base_url: Source URL.
            html: Page HTML content.
            max_jobs: Maximum number of jobs.

        Returns:
            Parsed jobs list.
        """

        if max_jobs <= 0:
            return []
        soup = BeautifulSoup(html, "html.parser")
        anchors = list(soup.select("div.posting a.posting-title, div.posting a"))
        if not anchors:
            fallback_anchors = list(soup.select("a[href]"))
            anchors = []
            for anchor in fallback_anchors:
                href = self._normalize_href(anchor.get("href"))
                if isinstance(href, str) and "/jobs/" in href:
                    anchors.append(anchor)

        jobs: list[JobCandidate] = []
        seen_urls: set[str] = set()
        for anchor in anchors:
            href = self._normalize_href(anchor.get("href"))
            title = anchor.get_text(" ", strip=True)
            if not href or not title:
                continue
            absolute_url = urljoin(base_url, href)
            if self._is_apply_link(absolute_url):
                continue
            if absolute_url in seen_urls:
                continue
            seen_urls.add(absolute_url)

            posting_root = anchor.find_parent(class_="posting")
            location_text = None
            if posting_root is not None:
                location_node = posting_root.select_one(
                    "span.sort-by-location"
                ) or posting_root.select_one("div.posting-categories")
                if location_node is not None:
                    location_text = location_node.get_text(" ", strip=True)

            jobs.append(
                JobCandidate(
                    external_id=self._extract_external_id(absolute_url),
                    title=title,
                    location=location_text,
                    company=company_from_url(base_url),
                    url=absolute_url,
                    raw={"source": "lever"},
                )
            )
            if len(jobs) >= max_jobs:
                break

        return jobs

    @staticmethod
    def _is_apply_link(job_url: str) -> bool:
        """Report whether a Lever URL points at an apply action, not a posting.

        Lever list pages render an ``Apply`` button anchor inside each
        ``div.posting`` alongside the posting-title link. Its href is the
        posting URL with a trailing ``/apply`` segment. Treating it as a
        distinct posting produces a phantom job titled ``Apply`` that shares the
        real posting's location. Such anchors must be ignored.

        Args:
            job_url: Absolute candidate URL.

        Returns:
            True when the URL's final path segment is ``apply``.
        """

        parts = [part for part in urlparse(job_url).path.split("/") if part]
        return bool(parts) and parts[-1].lower() == "apply"

    @staticmethod
    def _extract_external_id(job_url: str) -> str | None:
        """Extract a stable external id from a Lever URL.

        Args:
            job_url: Lever job URL.

        Returns:
            External id string when inferable.
        """

        parsed = urlparse(job_url)
        parts = [part for part in parsed.path.split("/") if part]
        if not parts:
            return None
        return parts[-1]

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

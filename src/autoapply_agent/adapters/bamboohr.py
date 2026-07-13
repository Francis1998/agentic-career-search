"""BambooHR hosted careers adapter (public JSON board).

BambooHR (``{tenant}.bamboohr.com``) is a widely adopted HRIS/ATS for
small-to-mid-sized employers. Unlike the HTML-scraping adapters in this package
(greenhouse, lever, ashby, workable, recruitee, smartrecruiters, teamtailor,
personio), BambooHR does not render postings as anchors on the careers page;
instead the hosted careers site is a client-rendered app backed by a public
JSON endpoint at ``{origin}/careers/list``. That endpoint returns
``{"result": [{"id", "jobOpeningName", "location", "isRemote"}, ...]}`` and each
posting's public page is ``{origin}/careers/{id}``.

This adapter is the package's first structured-JSON source: it derives the
tenant origin from any BambooHR careers URL, reads the list endpoint, and maps
each opening onto the shared :class:`JobCandidate` contract, guarding against the
blank-id rows BambooHR occasionally emits (which would otherwise collapse
distinct postings under URL dedup).
"""

from __future__ import annotations

import json
from urllib.parse import urljoin, urlparse

from autoapply_agent.adapters.base import (
    CareerSourceAdapter,
    JobCandidate,
    SourceAdapterError,
    company_from_url,
)

_LIST_PATH = "careers/list"
_LOCATION_FIELDS = ("city", "state", "country")


class BambooHrAdapter(CareerSourceAdapter):
    """Fetch jobs from a public BambooHR hosted careers board."""

    adapter_name = "bamboohr"

    def __init__(self, user_agent: str) -> None:
        """Create adapter instance.

        Args:
            user_agent: HTTP user agent string.
        """

        self._user_agent = user_agent

    async def fetch_jobs(
        self, base_url: str, timeout_seconds: float, max_jobs: int
    ) -> list[JobCandidate]:
        """Fetch and parse BambooHR jobs from the public list endpoint.

        Args:
            base_url: Any BambooHR careers URL for the tenant (for example
                ``https://acme.bamboohr.com/careers``).
            timeout_seconds: Request timeout in seconds.
            max_jobs: Maximum number of jobs.

        Returns:
            Parsed job candidates.
        """

        if max_jobs <= 0:
            return []
        list_url = self._list_url(base_url)
        payload = await self._request_html(list_url, timeout_seconds, self._user_agent)
        return self._parse_payload(list_url, payload, max_jobs)

    def _parse_payload(self, list_url: str, payload: str, max_jobs: int) -> list[JobCandidate]:
        """Parse the BambooHR ``/careers/list`` JSON payload into candidates.

        Args:
            list_url: The resolved list endpoint URL, used to derive the tenant
                origin for posting URLs and the fallback company token.
            payload: Raw JSON response body from the list endpoint.
            max_jobs: Maximum number of jobs.

        Returns:
            Parsed jobs list.

        Raises:
            SourceAdapterError: If the payload is not valid JSON.
        """

        if max_jobs <= 0:
            return []
        try:
            document = json.loads(payload)
        except (json.JSONDecodeError, ValueError) as exc:
            raise SourceAdapterError(f"invalid BambooHR JSON payload for {list_url}") from exc

        openings = document.get("result") if isinstance(document, dict) else None
        if not isinstance(openings, list):
            return []

        origin = self._origin(list_url)
        jobs: list[JobCandidate] = []
        seen_urls: set[str] = set()
        for opening in openings:
            candidate = self._build_candidate(origin, list_url, opening)
            if candidate is None or candidate.url in seen_urls:
                continue
            seen_urls.add(candidate.url)
            jobs.append(candidate)
            if len(jobs) >= max_jobs:
                break
        return jobs

    @classmethod
    def _build_candidate(cls, origin: str, list_url: str, opening: object) -> JobCandidate | None:
        """Build a candidate from a single BambooHR opening record.

        Records without a non-blank ``id`` or a usable ``jobOpeningName`` are
        skipped: a blank id would otherwise yield the bare ``/careers/`` URL for
        every such row and collapse them all under URL deduplication.

        Args:
            origin: Tenant origin (``scheme://host``) for posting URLs.
            list_url: List endpoint URL, used for the fallback company token.
            opening: A single decoded opening record.

        Returns:
            A :class:`JobCandidate` when the record is usable, else None.
        """

        if not isinstance(opening, dict):
            return None
        job_id = cls._clean_str(opening.get("id"))
        title = cls._clean_str(opening.get("jobOpeningName"))
        if job_id is None or title is None:
            return None

        return JobCandidate(
            external_id=job_id,
            title=title,
            location=cls._extract_location(opening),
            company=company_from_url(list_url),
            url=urljoin(f"{origin}/", f"careers/{job_id}"),
            raw={"source": "bamboohr"},
        )

    @classmethod
    def _extract_location(cls, opening: dict[str, object]) -> str | None:
        """Resolve a human-readable location for a BambooHR opening.

        BambooHR expresses location either as a nested object
        (``{"city", "state", "country"}``) or as a bare string; a remote-only
        opening may instead carry ``isRemote`` with no location. All forms are
        handled, falling back to ``Remote`` when the opening is flagged remote.

        Args:
            opening: A single decoded opening record.

        Returns:
            Location string when derivable, else None.
        """

        location = opening.get("location")
        if isinstance(location, str):
            resolved = location.strip() or None
        elif isinstance(location, dict):
            parts = [
                value.strip()
                for field in _LOCATION_FIELDS
                if isinstance((value := location.get(field)), str) and value.strip()
            ]
            resolved = ", ".join(parts) or None
        else:
            resolved = None

        if resolved is None and opening.get("isRemote") is True:
            return "Remote"
        return resolved

    @classmethod
    def _list_url(cls, base_url: str) -> str:
        """Derive the ``/careers/list`` endpoint URL from any careers URL.

        Args:
            base_url: Any BambooHR careers URL for the tenant.

        Returns:
            The tenant's ``{origin}/careers/list`` endpoint URL.
        """

        return f"{cls._origin(base_url)}/{_LIST_PATH}"

    @staticmethod
    def _origin(url: str) -> str:
        """Return the ``scheme://host`` origin for a URL.

        Args:
            url: Any absolute URL.

        Returns:
            The origin string, defaulting the scheme to ``https`` when absent.
        """

        parsed = urlparse(url)
        scheme = parsed.scheme or "https"
        return f"{scheme}://{parsed.netloc}"

    @staticmethod
    def _clean_str(value: object) -> str | None:
        """Coerce an id/name value to a trimmed non-empty string.

        Args:
            value: Raw JSON value (string or integer).

        Returns:
            The trimmed string when non-empty, else None.
        """

        if isinstance(value, bool):
            return None
        if isinstance(value, (str, int)):
            text = str(value).strip()
            return text or None
        return None

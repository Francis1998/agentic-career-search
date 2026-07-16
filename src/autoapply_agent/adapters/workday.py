"""Workday public careers CXS JSON adapter.

Workday (``{tenant}.wd{N}.myworkdayjobs.com``) hosts the majority of large-
enterprise career sites. Unlike the HTML-scraping adapters in this package, the
public listing page is a client-rendered SPA whose postings only appear after
JavaScript runs. The same SPA talks to Workday's public Candidate Experience
Service (CXS) at ``POST /wday/cxs/{tenant}/{site}/jobs`` with a JSON body of
``{"appliedFacets": {}, "limit": 20, "offset": N, "searchText": ""}``.

Each listing entry carries ``title``, ``locationsText``, and ``externalPath``
(e.g. ``/job/US-CA-Santa-Clara/Role-Title_JR2018189``). The public detail URL is
``{origin}/{locale}/{site}{externalPath}`` (locale defaults to ``en-US`` when the
careers URL omits one). The hard page size is 20 — requesting a larger limit
returns an empty ``jobPostings`` array with no error — so pagination advances
``offset`` by the number of postings received until ``max_jobs`` is satisfied or
a short page arrives.

This adapter is the package's second structured-JSON source (after BambooHR) and
the first that issues an authenticated-free POST against a public board API.
"""

from __future__ import annotations

import json
import re
from urllib.parse import urljoin, urlparse

import httpx

from autoapply_agent.adapters.base import (
    CareerSourceAdapter,
    JobCandidate,
    SourceAdapterError,
    company_from_url,
)

_PAGE_LIMIT = 20
_HOST_PATTERN = re.compile(
    r"^(?P<tenant>[^.]+)\.wd\d+\.myworkdayjobs\.com$",
    re.IGNORECASE,
)
_LOCALE_SEGMENT = re.compile(r"^[a-z]{2}(?:-[A-Za-z]{2})?$")
_REQ_ID_PATTERN = re.compile(r"_([A-Za-z0-9-]+)$")


class WorkdayAdapter(CareerSourceAdapter):
    """Fetch jobs from a public Workday myworkdayjobs.com CXS board."""

    adapter_name = "workday"

    def __init__(self, user_agent: str) -> None:
        """Create adapter instance.

        Args:
            user_agent: HTTP user agent string.
        """

        self._user_agent = user_agent

    async def fetch_jobs(
        self, base_url: str, timeout_seconds: float, max_jobs: int
    ) -> list[JobCandidate]:
        """Fetch and parse Workday jobs via the public CXS listing API.

        Args:
            base_url: Any Workday careers URL for the tenant/site (for example
                ``https://nvidia.wd5.myworkdayjobs.com/en-US/NVIDIAExternalCareerSite``).
            timeout_seconds: Request timeout in seconds.
            max_jobs: Maximum number of jobs.

        Returns:
            Parsed job candidates.
        """

        if max_jobs <= 0:
            return []
        board = self._parse_board(base_url)
        jobs: list[JobCandidate] = []
        seen_urls: set[str] = set()
        offset = 0
        while len(jobs) < max_jobs:
            page_limit = min(_PAGE_LIMIT, max_jobs - len(jobs))
            payload = await self._request_cxs_page(
                board["cxs_url"],
                board["origin"],
                board["site"],
                timeout_seconds,
                limit=page_limit,
                offset=offset,
            )
            page = self._parse_payload(board, payload, max_jobs - len(jobs))
            if not page:
                break
            for candidate in page:
                if candidate.url in seen_urls:
                    continue
                seen_urls.add(candidate.url)
                jobs.append(candidate)
                if len(jobs) >= max_jobs:
                    break
            if len(page) < page_limit:
                break
            offset += len(page)
        return jobs

    def _parse_payload(
        self, board: dict[str, str], payload: str, max_jobs: int
    ) -> list[JobCandidate]:
        """Parse one CXS listing page into candidates.

        Args:
            board: Parsed board coordinates (origin/tenant/site/locale/cxs_url).
            payload: Raw JSON response body from the CXS listing endpoint.
            max_jobs: Maximum number of jobs for this page slice.

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
            raise SourceAdapterError(
                f"invalid Workday JSON payload for {board['cxs_url']}"
            ) from exc

        postings = document.get("jobPostings") if isinstance(document, dict) else None
        if not isinstance(postings, list):
            return []

        jobs: list[JobCandidate] = []
        for posting in postings:
            candidate = self._build_candidate(board, posting)
            if candidate is None:
                continue
            jobs.append(candidate)
            if len(jobs) >= max_jobs:
                break
        return jobs

    @classmethod
    def _build_candidate(cls, board: dict[str, str], posting: object) -> JobCandidate | None:
        """Build a candidate from a single Workday CXS posting record.

        Records without a usable ``title`` or ``externalPath`` are skipped: a
        blank path would otherwise yield a bare site URL and collapse distinct
        postings under URL deduplication.

        Args:
            board: Parsed board coordinates.
            posting: A single decoded posting record.

        Returns:
            A :class:`JobCandidate` when the record is usable, else None.
        """

        if not isinstance(posting, dict):
            return None
        title = cls._clean_str(posting.get("title"))
        external_path = cls._clean_str(posting.get("externalPath"))
        if title is None or external_path is None:
            return None
        if not external_path.startswith("/"):
            external_path = f"/{external_path}"

        detail_url = urljoin(
            f"{board['origin']}/",
            f"{board['locale']}/{board['site']}{external_path}",
        )
        return JobCandidate(
            external_id=cls._extract_external_id(external_path),
            title=title,
            location=cls._clean_str(posting.get("locationsText")),
            company=company_from_url(board["origin"]),
            url=detail_url,
            raw={"source": "workday"},
        )

    @classmethod
    def _parse_board(cls, base_url: str) -> dict[str, str]:
        """Derive CXS coordinates from any Workday careers URL.

        Args:
            base_url: Any ``*.myworkdayjobs.com`` careers URL.

        Returns:
            Mapping with ``origin``, ``tenant``, ``site``, ``locale``, ``cxs_url``.

        Raises:
            SourceAdapterError: If the URL is not a recognisable Workday board.
        """

        parsed = urlparse(base_url)
        host = (parsed.hostname or "").lower()
        match = _HOST_PATTERN.match(host)
        if match is None:
            raise SourceAdapterError(f"unrecognised Workday careers host for {base_url}")
        tenant = match.group("tenant")
        segments = [segment for segment in parsed.path.split("/") if segment]
        locale = "en-US"
        site: str | None = None
        if segments and _LOCALE_SEGMENT.match(segments[0]):
            locale = segments[0]
            site = segments[1] if len(segments) > 1 else None
        elif segments:
            site = segments[0]
        if not site or site.lower() in {"wday", "cxs", "job", "jobs"}:
            raise SourceAdapterError(f"missing Workday site slug in careers URL {base_url}")
        scheme = parsed.scheme or "https"
        origin = f"{scheme}://{parsed.netloc}"
        cxs_url = f"{origin}/wday/cxs/{tenant}/{site}/jobs"
        return {
            "origin": origin,
            "tenant": tenant,
            "site": site,
            "locale": locale,
            "cxs_url": cxs_url,
        }

    async def _request_cxs_page(
        self,
        cxs_url: str,
        origin: str,
        site: str,
        timeout_seconds: float,
        *,
        limit: int,
        offset: int,
    ) -> str:
        """POST one page of the public CXS listing endpoint.

        Args:
            cxs_url: Fully-qualified CXS listing URL.
            origin: Board origin used for the Referer header.
            site: Site slug used for the Referer header.
            timeout_seconds: Request timeout in seconds.
            limit: Page size (capped at 20 by Workday).
            offset: Zero-based offset into the listing.

        Returns:
            Raw response body text.

        Raises:
            SourceAdapterError: If the request fails or times out.
        """

        timeout = httpx.Timeout(timeout_seconds)
        headers = {
            "User-Agent": self._user_agent,
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Referer": f"{origin}/en-US/{site}",
        }
        body = {
            "appliedFacets": {},
            "limit": min(limit, _PAGE_LIMIT),
            "offset": max(offset, 0),
            "searchText": "",
        }
        try:
            async with httpx.AsyncClient(
                timeout=timeout, follow_redirects=True, headers=headers
            ) as client:
                response = await client.post(cxs_url, json=body)
                response.raise_for_status()
                return response.text
        except httpx.TimeoutException as exc:
            raise SourceAdapterError(f"request timed out for {cxs_url}") from exc
        except httpx.HTTPStatusError as exc:
            raise SourceAdapterError(
                f"http error {exc.response.status_code} for {cxs_url}",
            ) from exc
        except httpx.RequestError as exc:
            raise SourceAdapterError(f"request failed for {cxs_url}: {exc!s}") from exc

    @staticmethod
    def _extract_external_id(external_path: str) -> str | None:
        """Extract the requisition id trailing the final underscore in the path.

        Args:
            external_path: Workday ``externalPath`` (e.g. ``/job/.../Role_JR1``).

        Returns:
            The trailing requisition token when present, else None.
        """

        leaf = external_path.rstrip("/").rsplit("/", 1)[-1]
        match = _REQ_ID_PATTERN.search(leaf)
        if match is None:
            return None
        return match.group(1)

    @staticmethod
    def _clean_str(value: object) -> str | None:
        """Coerce a title/path/location value to a trimmed non-empty string.

        Args:
            value: Raw JSON value.

        Returns:
            The trimmed string when non-empty, else None.
        """

        if isinstance(value, bool):
            return None
        if isinstance(value, (str, int)):
            text = str(value).strip()
            return text or None
        return None

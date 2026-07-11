"""Base adapter contract for parsing public career pages."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

_LOCATION_CLASS_TOKEN = re.compile(r"(?:^|[-_])location", re.IGNORECASE)


@dataclass(slots=True, frozen=True)
class JobCandidate:
    """Normalized job candidate returned by source adapters."""

    external_id: str | None
    title: str
    location: str | None
    company: str | None
    url: str
    raw: dict[str, object] | None


class SourceAdapterError(RuntimeError):
    """Represents source adapter request or parsing failures."""


class CareerSourceAdapter(ABC):
    """Abstract source adapter for fetching and parsing jobs."""

    adapter_name: str

    @abstractmethod
    async def fetch_jobs(
        self, base_url: str, timeout_seconds: float, max_jobs: int
    ) -> list[JobCandidate]:
        """Fetch and parse job candidates from a source URL.

        Args:
            base_url: Public source URL.
            timeout_seconds: Per-request timeout.
            max_jobs: Maximum number of jobs to return.

        Returns:
            Parsed job candidates list.
        """

    async def _request_html(self, base_url: str, timeout_seconds: float, user_agent: str) -> str:
        """Fetch HTML body with explicit timeout and error mapping.

        Args:
            base_url: Public source URL.
            timeout_seconds: Request timeout in seconds.
            user_agent: Outbound HTTP user agent.

        Returns:
            HTML body string.

        Raises:
            SourceAdapterError: If request fails or times out.
        """

        timeout = httpx.Timeout(timeout_seconds)
        headers = {"User-Agent": user_agent}
        try:
            async with httpx.AsyncClient(
                timeout=timeout, follow_redirects=True, headers=headers
            ) as client:
                response = await client.get(base_url)
                response.raise_for_status()
                return response.text
        except httpx.TimeoutException as exc:
            raise SourceAdapterError(f"request timed out for {base_url}") from exc
        except httpx.HTTPStatusError as exc:
            raise SourceAdapterError(
                f"http error {exc.response.status_code} for {base_url}",
            ) from exc
        except httpx.RequestError as exc:
            raise SourceAdapterError(f"request failed for {base_url}: {exc!s}") from exc


def company_from_url(base_url: str) -> str:
    """Infer a lightweight company identifier from URL hostname.

    Args:
        base_url: Source URL.

    Returns:
        Best-effort company token.
    """

    host = urlparse(base_url).hostname or "unknown"
    return host.removeprefix("www.")


def find_location_text(anchor: object, container_class_pattern: re.Pattern[str]) -> str | None:
    """Resolve a posting location from an anchor's surrounding markup.

    The location is looked up within the anchor's nearest posting container
    (a ``class`` matching ``container_class_pattern``) so a posting without its
    own location does not inherit a sibling's location. A location element is
    identified by a ``class`` token that *is* ``location`` (optionally
    hyphen/underscore-delimited, e.g. ``job-location`` or ``posting__location``)
    rather than by any class merely containing the substring ``location`` \u2014 the
    latter would misread a ``relocation`` badge as the posting's location.

    Args:
        anchor: BeautifulSoup anchor element for the posting.
        container_class_pattern: Compiled pattern matching the posting
            container's ``class``.

    Returns:
        Location text when discoverable, else None.
    """

    find_parent = getattr(anchor, "find_parent", None)
    if find_parent is None:
        return None
    container = find_parent(attrs={"class": container_class_pattern})
    scope = container if container is not None else getattr(anchor, "parent", None)
    if scope is None:
        return None
    find_all = getattr(scope, "find_all", None)
    if find_all is None:
        return None
    for node in find_all(True):
        classes = node.get("class") or []
        if any(_LOCATION_CLASS_TOKEN.search(token) for token in classes):
            text = node.get_text(" ", strip=True)
            if text:
                return text
    return None

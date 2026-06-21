"""Base adapter contract for parsing public career pages."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx


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
    return host.replace("www.", "")

"""Time helpers for timezone-aware UTC timestamps."""

from __future__ import annotations

from datetime import UTC, datetime


def utc_now() -> datetime:
    """Return the current timezone-aware UTC timestamp.

    Returns:
        Current time with UTC tzinfo.
    """

    return datetime.now(UTC)

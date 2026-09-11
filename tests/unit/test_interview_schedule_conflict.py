"""Unit tests for InterviewScheduleConflictGuard."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from autoapply_agent.services.interview_schedule_conflict import (
    ConflictReport,
    InterviewScheduleConflictGuard,
    InterviewSlot,
)

if TYPE_CHECKING:
    from _pytest.capture import CaptureFixture
    from _pytest.fixtures import FixtureRequest
    from _pytest.logging import LogCaptureFixture
    from _pytest.monkeypatch import MonkeyPatch
    from pytest_mock.plugin import MockerFixture


def _slot(start: str, end: str, label: str) -> InterviewSlot:
    return InterviewSlot(start_iso=start, end_iso=end, label=label)


def test_bad_range_raises() -> None:
    """end_iso <= start_iso raises ValueError."""

    with pytest.raises(ValueError, match="end_iso"):
        InterviewScheduleConflictGuard().check(
            proposed=_slot("2026-09-15T10:00:00", "2026-09-15T09:00:00", "Acme"),
            existing=[],
        )


def test_blank_label_raises() -> None:
    """Blank proposed label raises ValueError."""

    with pytest.raises(ValueError, match="label"):
        InterviewScheduleConflictGuard().check(
            proposed=_slot("2026-09-15T10:00:00", "2026-09-15T11:00:00", "  "),
            existing=[],
        )


def test_invalid_iso_raises() -> None:
    """Unparseable ISO datetimes raise ValueError."""

    with pytest.raises(ValueError, match="ISO"):
        InterviewScheduleConflictGuard().check(
            proposed=_slot("not-a-date", "2026-09-15T11:00:00", "Acme"),
            existing=[],
        )


def test_overlap_detected() -> None:
    """Overlapping existing slots are listed as conflicts."""

    proposed = _slot("2026-09-15T10:00:00", "2026-09-15T11:00:00", "Acme onsite")
    blocking = _slot("2026-09-15T10:30:00", "2026-09-15T11:30:00", "Globex screen")
    free = _slot("2026-09-15T12:00:00", "2026-09-15T13:00:00", "Prep block")

    report = InterviewScheduleConflictGuard().check(
        proposed=proposed,
        existing=[blocking, free],
    )
    assert isinstance(report, ConflictReport)
    assert report.has_conflict is True
    assert report.conflicts == [blocking]
    assert report.requires_human_review is True
    assert report.calendar_mutated is False


def test_touching_endpoints_not_conflict() -> None:
    """Adjacent windows that only touch at an endpoint are not conflicts."""

    report = InterviewScheduleConflictGuard().check(
        proposed=_slot("2026-09-15T11:00:00", "2026-09-15T12:00:00", "Acme"),
        existing=[_slot("2026-09-15T10:00:00", "2026-09-15T11:00:00", "Prep")],
    )
    assert report.has_conflict is False
    assert report.conflicts == []


def test_no_conflict_empty_existing() -> None:
    """Empty existing list yields no conflicts but still requires HITL."""

    proposed = _slot("2026-09-15T10:00:00", "2026-09-15T11:00:00", "Acme")
    report = InterviewScheduleConflictGuard().check(proposed=proposed, existing=[])
    assert report.has_conflict is False
    assert report.conflicts == []
    assert report.requires_human_review is True
    assert report.calendar_mutated is False
    assert report.proposed.label == "Acme"


def test_never_mutates_calendar_requires_human_review() -> None:
    """Every payload flags HITL review and never mutates calendars."""

    report = InterviewScheduleConflictGuard().check(
        proposed=_slot("2026-09-15T14:00:00", "2026-09-15T15:00:00", "Loop"),
        existing=[_slot("2026-09-15T14:00:00", "2026-09-15T14:30:00", "Busy")],
    )
    assert report.requires_human_review is True
    assert report.calendar_mutated is False
    assert report.has_conflict is True


def test_no_network_calls() -> None:
    """Guard never performs HTTP calls."""

    with (
        patch("httpx.Client", MagicMock()) as client_cls,
        patch("httpx.AsyncClient", MagicMock()) as async_cls,
        patch("httpx.get", MagicMock()) as get_fn,
        patch("httpx.post", MagicMock()) as post_fn,
    ):
        InterviewScheduleConflictGuard().check(
            proposed=_slot("2026-09-15T10:00:00", "2026-09-15T11:00:00", "Acme"),
            existing=[],
        )
        client_cls.assert_not_called()
        async_cls.assert_not_called()
        get_fn.assert_not_called()
        post_fn.assert_not_called()


def test_deterministic() -> None:
    """Repeated check calls are identical."""

    guard = InterviewScheduleConflictGuard()
    kwargs = {
        "proposed": _slot("2026-09-15T10:00:00", "2026-09-15T11:00:00", "Acme"),
        "existing": [
            _slot("2026-09-15T10:30:00", "2026-09-15T11:30:00", "Globex"),
            _slot("2026-09-16T09:00:00", "2026-09-16T10:00:00", "Prep"),
        ],
    }
    assert guard.check(**kwargs) == guard.check(**kwargs)

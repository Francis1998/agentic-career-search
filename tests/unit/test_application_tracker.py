"""Unit tests for the application tracker's state machine, follow-ups and iCalendar text."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from autoapply_agent.services.application_export import fold_line, ics_datetime, ics_escape
from autoapply_agent.services.application_stages import (
    PIPELINE_ORDER,
    ApplicationStage,
    ApplicationStageError,
    allowed_next_stages,
    check_transition,
)
from autoapply_agent.services.application_tracker import FollowUpStatus, follow_up_status

NOW = datetime(2026, 11, 19, 12, 0, tzinfo=UTC)
S = ApplicationStage


def test_pipeline_order_covers_every_stage_once() -> None:
    assert sorted(PIPELINE_ORDER) == sorted(ApplicationStage)
    assert len(set(PIPELINE_ORDER)) == len(PIPELINE_ORDER)


@pytest.mark.parametrize(
    ("stage", "expected"),
    [
        (S.SAVED, (S.APPLIED, S.REJECTED)),
        (S.APPLIED, (S.INTERVIEW, S.REJECTED)),
        (S.INTERVIEW, (S.OFFER, S.REJECTED)),
        (S.OFFER, (S.ACCEPTED, S.REJECTED)),
        (S.ACCEPTED, ()),
        (S.REJECTED, ()),
    ],
)
def test_allowed_next_stages_follow_the_pipeline(
    stage: ApplicationStage, expected: tuple[ApplicationStage, ...]
) -> None:
    assert allowed_next_stages(stage) == expected
    for target in expected:
        check_transition(stage, target)
    check_transition(stage, stage)


def test_illegal_transitions_name_the_legal_ones() -> None:
    with pytest.raises(ApplicationStageError, match=r"^cannot move from saved to offer"):
        check_transition(S.SAVED, S.OFFER)
    with pytest.raises(ApplicationStageError, match=r"\(allowed: applied, rejected\)$"):
        check_transition(S.SAVED, S.INTERVIEW)
    with pytest.raises(ApplicationStageError, match=r"\(accepted is a final stage\)$"):
        check_transition(S.ACCEPTED, S.REJECTED)


@pytest.mark.parametrize(
    ("offset", "expected"),
    [
        (None, FollowUpStatus.NONE),
        (-timedelta(seconds=1), FollowUpStatus.OVERDUE),
        (timedelta(0), FollowUpStatus.DUE),
        (timedelta(days=7), FollowUpStatus.DUE),
        (timedelta(days=7, seconds=1), FollowUpStatus.SCHEDULED),
    ],
)
def test_follow_up_status_boundaries(offset: timedelta | None, expected: FollowUpStatus) -> None:
    moment = None if offset is None else NOW + offset
    assert follow_up_status(moment, NOW) is expected


def test_naive_follow_up_times_are_utc() -> None:
    naive = (NOW - timedelta(minutes=1)).replace(tzinfo=None)
    assert follow_up_status(naive, NOW) is FollowUpStatus.OVERDUE


def test_ics_escape_handles_text_specials_line_breaks_and_controls() -> None:
    assert ics_escape("a\\b;c,d") == "a\\\\b\\;c\\,d"
    assert ics_escape("one\r\ntwo\rthree\nfour") == "one\\ntwo\\nthree\\nfour"
    assert ics_escape("tab\tkept\x00\x07\x1b\x7fgone") == "tab\tkeptgone"
    assert ics_escape("BEGIN:VEVENT\nEND:VCALENDAR") == "BEGIN:VEVENT\\nEND:VCALENDAR"


@pytest.mark.parametrize("text", ["x" * 200, "é" * 120, "🙂" * 50, "a" + "日本" * 60])
def test_fold_line_keeps_lines_within_75_octets_without_splitting_characters(text: str) -> None:
    line = f"SUMMARY:{text}"

    folded = fold_line(line)

    parts = folded.split("\r\n")
    assert all(len(part.encode("utf-8")) <= 75 for part in parts)
    assert all(part.startswith(" ") for part in parts[1:])
    assert "".join([parts[0], *(part[1:] for part in parts[1:])]) == line


def test_short_lines_are_not_folded() -> None:
    assert fold_line("VERSION:2.0") == "VERSION:2.0"
    assert fold_line("X" * 75) == "X" * 75


def test_ics_datetime_is_zero_padded_utc() -> None:
    assert ics_datetime(datetime(999, 1, 2, 3, 4, 5, tzinfo=UTC)) == "09990102T030405Z"
    assert ics_datetime(datetime(2030, 1, 2, 9, 30)) == "20300102T093000Z"
    offset = datetime.fromisoformat("2030-01-02T09:30:00-08:00")
    assert ics_datetime(offset) == "20300102T173000Z"

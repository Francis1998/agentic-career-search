"""Unit tests for ApplicationStageTracker (CRM-lite pipeline)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from autoapply_agent.services.application_stages import (
    ApplicationStage,
    ApplicationStageError,
    ApplicationStageTracker,
)

if TYPE_CHECKING:
    from _pytest.capture import CaptureFixture
    from _pytest.fixtures import FixtureRequest
    from _pytest.logging import LogCaptureFixture
    from _pytest.monkeypatch import MonkeyPatch
    from pytest_mock.plugin import MockerFixture


def test_upsert_creates_saved_record() -> None:
    """New jobs can be upserted into the saved stage."""

    tracker = ApplicationStageTracker()
    record = tracker.upsert("job-1", ApplicationStage.SAVED, note="interesting")
    assert record.job_key == "job-1"
    assert record.stage is ApplicationStage.SAVED
    assert record.note == "interesting"
    assert tracker.get("job-1") == record


def test_advance_moves_along_happy_path() -> None:
    """Advance walks saved → applied → interview → offer → accepted."""

    tracker = ApplicationStageTracker()
    tracker.upsert("job-1", ApplicationStage.SAVED)
    assert tracker.advance("job-1").stage is ApplicationStage.APPLIED
    assert tracker.advance("job-1").stage is ApplicationStage.INTERVIEW
    assert tracker.advance("job-1").stage is ApplicationStage.OFFER
    assert tracker.advance("job-1").stage is ApplicationStage.ACCEPTED
    with pytest.raises(ApplicationStageError):
        tracker.advance("job-1")


def test_reject_from_applied_is_allowed() -> None:
    """Applied jobs may transition to rejected."""

    tracker = ApplicationStageTracker()
    tracker.upsert("job-2", ApplicationStage.SAVED)
    tracker.advance("job-2")
    rejected = tracker.upsert("job-2", ApplicationStage.REJECTED, note="no reply")
    assert rejected.stage is ApplicationStage.REJECTED
    assert tracker.list_by_stage(ApplicationStage.REJECTED)[0].job_key == "job-2"


def test_illegal_transition_raises() -> None:
    """Skipping stages without an allowed edge raises."""

    tracker = ApplicationStageTracker()
    tracker.upsert("job-3", ApplicationStage.SAVED)
    with pytest.raises(ApplicationStageError):
        tracker.upsert("job-3", ApplicationStage.OFFER)


def test_empty_job_key_raises() -> None:
    """Blank job keys are rejected."""

    tracker = ApplicationStageTracker()
    with pytest.raises(ValueError):
        tracker.upsert("  ", ApplicationStage.SAVED)


def test_allowed_transitions_for_offer() -> None:
    """Offer may go to accepted or rejected only."""

    allowed = ApplicationStageTracker.allowed_transitions(ApplicationStage.OFFER)
    assert allowed == frozenset({ApplicationStage.ACCEPTED, ApplicationStage.REJECTED})

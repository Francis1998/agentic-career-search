"""Unit tests for ApplicationGhostingDetector."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from autoapply_agent.services.application_ghosting import ApplicationGhostingDetector

if TYPE_CHECKING:
    from _pytest.capture import CaptureFixture
    from _pytest.fixtures import FixtureRequest
    from _pytest.logging import LogCaptureFixture
    from _pytest.monkeypatch import MonkeyPatch
    from pytest_mock.plugin import MockerFixture


def test_empty_company_raises() -> None:
    """Blank company name raises ValueError."""

    with pytest.raises(ValueError, match="company"):
        ApplicationGhostingDetector().detect(
            company=" ",
            role="SWE",
            stage="applied",
            last_update_iso="2026-09-01",
            now_iso="2026-09-12",
        )


def test_bad_date_raises() -> None:
    """Invalid ISO dates raise ValueError."""

    with pytest.raises(ValueError, match="last_update_iso"):
        ApplicationGhostingDetector().detect(
            company="Acme",
            role="SWE",
            stage="applied",
            last_update_iso="not-a-date",
            now_iso="2026-09-12",
        )


def test_future_last_update_raises() -> None:
    """last_update after now raises ValueError."""

    with pytest.raises(ValueError, match="last_update_iso"):
        ApplicationGhostingDetector().detect(
            company="Acme",
            role="SWE",
            stage="applied",
            last_update_iso="2026-09-20",
            now_iso="2026-09-12",
        )


def test_fresh_urgency() -> None:
    """Fewer than 7 stall days maps to fresh."""

    status = ApplicationGhostingDetector().detect(
        company="Acme",
        role="Platform Engineer",
        stage="applied",
        last_update_iso="2026-09-10",
        now_iso="2026-09-12",
    )
    assert status.days_stalled == 2
    assert status.urgency == "fresh"


def test_cooling_urgency() -> None:
    """7-13 stall days maps to cooling."""

    status = ApplicationGhostingDetector().detect(
        company="Acme",
        role="SWE",
        stage="applied",
        last_update_iso="2026-09-01",
        now_iso="2026-09-12",
    )
    assert status.days_stalled == 11
    assert status.urgency == "cooling"


def test_stalled_urgency() -> None:
    """14-20 stall days maps to stalled."""

    status = ApplicationGhostingDetector().detect(
        company="Acme",
        role="SWE",
        stage="applied",
        last_update_iso="2026-08-25",
        now_iso="2026-09-12",
    )
    assert status.days_stalled == 18
    assert status.urgency == "stalled"


def test_likely_ghosted_urgency() -> None:
    """21+ stall days maps to likely_ghosted."""

    status = ApplicationGhostingDetector().detect(
        company="Acme",
        role="SWE",
        stage="applied",
        last_update_iso="2026-08-01",
        now_iso="2026-09-12",
    )
    assert status.days_stalled == 42
    assert status.urgency == "likely_ghosted"


def test_interview_stage_bias_escalates() -> None:
    """Interview stages apply +3 day bias toward higher urgency."""

    status = ApplicationGhostingDetector().detect(
        company="Globex",
        role="SRE",
        stage="interview",
        last_update_iso="2026-09-01",
        now_iso="2026-09-12",
    )
    assert status.days_stalled == 11
    assert status.urgency == "stalled"


def test_never_auto_nudges_requires_human_review() -> None:
    """Every payload flags HITL review and never auto-nudges."""

    status = ApplicationGhostingDetector().detect(
        company="Globex",
        role="SRE",
        stage="applied",
        last_update_iso="2026-09-01",
        now_iso="2026-09-12",
    )
    assert status.requires_human_review is True
    assert status.auto_nudge is False
    assert status.suggestions


def test_no_network_calls() -> None:
    """Detector never performs HTTP calls."""

    with (
        patch("httpx.Client", MagicMock()) as client_cls,
        patch("httpx.AsyncClient", MagicMock()) as async_cls,
        patch("httpx.get", MagicMock()) as get_fn,
        patch("httpx.post", MagicMock()) as post_fn,
    ):
        ApplicationGhostingDetector().detect(
            company="Acme",
            role="SWE",
            stage="applied",
            last_update_iso="2026-09-10",
            now_iso="2026-09-12",
        )
        client_cls.assert_not_called()
        async_cls.assert_not_called()
        get_fn.assert_not_called()
        post_fn.assert_not_called()

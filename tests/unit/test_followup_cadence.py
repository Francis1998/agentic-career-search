"""Unit tests for ApplicationFollowUpCadencePlanner."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from autoapply_agent.services.followup_cadence import ApplicationFollowUpCadencePlanner

if TYPE_CHECKING:
    from _pytest.capture import CaptureFixture
    from _pytest.fixtures import FixtureRequest
    from _pytest.logging import LogCaptureFixture
    from _pytest.monkeypatch import MonkeyPatch
    from pytest_mock.plugin import MockerFixture


def test_blank_company_raises() -> None:
    """Blank company raises ValueError."""

    with pytest.raises(ValueError, match="company"):
        ApplicationFollowUpCadencePlanner().plan(
            company=" ",
            role="Backend Engineer",
            applied_on="2026-09-14",
        )


def test_blank_applied_on_raises() -> None:
    """Blank applied_on raises ValueError."""

    with pytest.raises(ValueError, match="applied_on"):
        ApplicationFollowUpCadencePlanner().plan(
            company="Acme",
            role="Backend Engineer",
            applied_on="",
        )


def test_invalid_offset_raises() -> None:
    """Non-positive offsets raise ValueError."""

    with pytest.raises(ValueError, match="offsets_days"):
        ApplicationFollowUpCadencePlanner().plan(
            company="Acme",
            role="Backend Engineer",
            applied_on="2026-09-14",
            offsets_days=[0, 3],
        )


def test_builds_default_cadence_steps() -> None:
    """Default offsets yield ordered HITL steps across channels."""

    plan = ApplicationFollowUpCadencePlanner().plan(
        company="Acme",
        role="Backend Engineer",
        applied_on="2026-09-14",
        channels=["email", "linkedin"],
    )
    assert plan.company == "Acme"
    assert [step.day_offset for step in plan.steps] == [3, 7, 14]
    assert plan.steps[0].channel == "email"
    assert plan.steps[1].channel == "linkedin"
    assert "check-in" in plan.steps[0].action.lower()
    assert plan.guidance


def test_never_auto_nudges_requires_human_review() -> None:
    """Every payload flags HITL review and never auto-nudges."""

    plan = ApplicationFollowUpCadencePlanner().plan(
        company="Acme",
        role="PM",
        applied_on="2026-09-01",
    )
    assert plan.requires_human_review is True
    assert plan.auto_nudge is False


def test_no_network_calls() -> None:
    """Cadence planner never performs HTTP calls."""

    with (
        patch("httpx.Client", MagicMock()) as client_cls,
        patch("httpx.AsyncClient", MagicMock()) as async_cls,
        patch("httpx.get", MagicMock()) as get_fn,
        patch("httpx.post", MagicMock()) as post_fn,
    ):
        ApplicationFollowUpCadencePlanner().plan(
            company="Acme",
            role="Data Engineer",
            applied_on="2026-09-14",
        )
        client_cls.assert_not_called()
        async_cls.assert_not_called()
        get_fn.assert_not_called()
        post_fn.assert_not_called()

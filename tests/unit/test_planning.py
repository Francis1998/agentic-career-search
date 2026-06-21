"""Unit tests for deterministic planning service."""

from __future__ import annotations

from typing import TYPE_CHECKING

from autoapply_agent.adapters.base import JobCandidate
from autoapply_agent.services.planning import DeterministicPlanningService

if TYPE_CHECKING:
    from _pytest.capture import CaptureFixture
    from _pytest.fixtures import FixtureRequest
    from _pytest.logging import LogCaptureFixture
    from _pytest.monkeypatch import MonkeyPatch
    from pytest_mock.plugin import MockerFixture


def test_plan_contains_expected_steps() -> None:
    """Planner returns predictable actionable steps."""

    planning_service = DeterministicPlanningService()
    candidate = JobCandidate(
        external_id="123",
        title="Platform Engineer",
        location="Remote",
        company="example.net",
        url="https://example.net/jobs/123",
        raw=None,
    )

    steps = planning_service.plan(candidate, "python platform")

    assert len(steps) == 5
    assert steps[0].startswith("Open posting:")
    assert "Tailor resume" in steps[2]

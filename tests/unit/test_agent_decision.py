"""Unit tests for deterministic agent decision engine."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from autoapply_agent.adapters.base import JobCandidate
from autoapply_agent.services.agent_decision import (
    HIGH_PRIORITY_MIN_SCORE,
    MEDIUM_PRIORITY_MIN_SCORE,
    AgentDecisionEngine,
    priority_tier_for_score,
)
from autoapply_agent.services.planning import DeterministicPlanningService
from autoapply_agent.services.scoring import DeterministicScoringService

if TYPE_CHECKING:
    from _pytest.capture import CaptureFixture
    from _pytest.fixtures import FixtureRequest
    from _pytest.logging import LogCaptureFixture
    from _pytest.monkeypatch import MonkeyPatch
    from pytest_mock.plugin import MockerFixture


def test_agent_decision_contains_priority_rationale_and_plan() -> None:
    """Decision engine should output explainable deterministic decisions."""

    engine = AgentDecisionEngine(
        scoring_service=DeterministicScoringService(),
        planning_service=DeterministicPlanningService(),
    )
    candidate = JobCandidate(
        external_id="dec-1",
        title="Senior Python Platform Engineer",
        location="Remote",
        company="example.ai",
        url="https://example.ai/jobs/dec-1",
        raw={"source": "unit"},
    )

    decision = engine.evaluate(candidate, "python platform remote")

    assert decision.score > 0.6
    assert decision.priority_tier in {"low", "medium", "high"}
    assert len(decision.rationale) >= 3
    assert any("Matched query terms" in line for line in decision.rationale)
    assert decision.plan_steps[1].startswith("Triage priority:")


@pytest.mark.parametrize(
    ("score", "tier"),
    [
        (0.99, "high"),
        (HIGH_PRIORITY_MIN_SCORE, "high"),
        (0.7999, "medium"),
        (MEDIUM_PRIORITY_MIN_SCORE, "medium"),
        (0.6499, "low"),
        (0.0, "low"),
    ],
)
def test_priority_tier_for_score_boundaries(score: float, tier: str) -> None:
    """Tier thresholds are inclusive lower bounds shared with the decision engine."""

    assert priority_tier_for_score(score) == tier
    assert AgentDecisionEngine._priority_tier(score) == tier

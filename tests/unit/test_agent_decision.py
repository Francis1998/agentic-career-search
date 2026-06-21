"""Unit tests for deterministic agent decision engine."""

from __future__ import annotations

from typing import TYPE_CHECKING

from autoapply_agent.adapters.base import JobCandidate
from autoapply_agent.services.agent_decision import AgentDecisionEngine
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

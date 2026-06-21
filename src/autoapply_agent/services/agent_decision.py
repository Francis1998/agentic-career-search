"""Agent decision engine for scoring, rationale, and planning."""

from __future__ import annotations

from dataclasses import dataclass

from autoapply_agent.adapters.base import JobCandidate
from autoapply_agent.services.planning import DeterministicPlanningService
from autoapply_agent.services.scoring import DeterministicScoringService


@dataclass(slots=True, frozen=True)
class AgentDecision:
    """Decision output for one candidate evaluation."""

    score: float
    matched_query_terms: list[str]
    priority_tier: str
    rationale: list[str]
    plan_steps: list[str]


class AgentDecisionEngine:
    """Compose deterministic scoring and planning into one decision output."""

    def __init__(
        self,
        scoring_service: DeterministicScoringService,
        planning_service: DeterministicPlanningService,
    ) -> None:
        """Initialize decision engine dependencies.

        Args:
            scoring_service: Scoring service used for relevance.
            planning_service: Planning service used for next-step generation.
        """

        self._scoring_service = scoring_service
        self._planning_service = planning_service

    def evaluate(self, job_candidate: JobCandidate, query: str | None) -> AgentDecision:
        """Evaluate one job candidate and produce an agent decision package.

        Args:
            job_candidate: Job candidate from source adapter.
            query: Optional user objective query.

        Returns:
            AgentDecision with score, rationale, tier, and action plan.
        """

        score = self._scoring_service.score(job_candidate, query)
        matched_terms = self._scoring_service.match_terms(job_candidate, query)
        priority_tier = self._priority_tier(score)
        rationale = self._build_rationale(job_candidate, matched_terms, priority_tier)
        plan_steps = self._planning_service.plan(
            job_candidate=job_candidate,
            query=query,
            priority_tier=priority_tier,
        )
        return AgentDecision(
            score=score,
            matched_query_terms=matched_terms,
            priority_tier=priority_tier,
            rationale=rationale,
            plan_steps=plan_steps,
        )

    @staticmethod
    def _priority_tier(score: float) -> str:
        """Convert numeric score to an execution priority tier.

        Args:
            score: Relevance score in range [0.0, 1.0].

        Returns:
            Priority tier string.
        """

        if score >= 0.8:
            return "high"
        if score >= 0.65:
            return "medium"
        return "low"

    @staticmethod
    def _build_rationale(
        job_candidate: JobCandidate,
        matched_terms: list[str],
        priority_tier: str,
    ) -> list[str]:
        """Build deterministic rationale lines for traceable decisions.

        Args:
            job_candidate: Candidate being evaluated.
            matched_terms: Query terms matched in candidate text.
            priority_tier: Derived priority tier.

        Returns:
            Ordered rationale bullets.
        """

        rationale_lines: list[str] = [
            f"Priority tier set to {priority_tier} from deterministic score.",
            f"Role title considered: {job_candidate.title}.",
        ]
        if matched_terms:
            rationale_lines.append(f"Matched query terms: {', '.join(matched_terms)}.")
        else:
            rationale_lines.append(
                "No direct query-term match; ranking relies on baseline relevance."
            )
        if job_candidate.location:
            rationale_lines.append(f"Location signal observed: {job_candidate.location}.")
        return rationale_lines

"""Deterministic planning service for next job actions."""

from __future__ import annotations

from autoapply_agent.adapters.base import JobCandidate


class DeterministicPlanningService:
    """Create deterministic action plans from a job candidate."""

    def plan(
        self,
        job_candidate: JobCandidate,
        query: str | None,
        priority_tier: str = "medium",
    ) -> list[str]:
        """Build deterministic application plan steps.

        Args:
            job_candidate: Candidate to plan for.
            query: Optional run query string.
            priority_tier: Priority hint from decision engine.

        Returns:
            Ordered plan steps.
        """

        stripped_query = query.strip() if query else ""
        query_hint = stripped_query or "target role requirements"
        company_text = job_candidate.company or "the employer"

        return [
            f"Open posting: {job_candidate.url}",
            f"Triage priority: {priority_tier}",
            f"Validate fit against query: {query_hint}",
            f"Tailor resume to role title: {job_candidate.title}",
            f"Draft cover note referencing {company_text}",
            "Submit application and capture confirmation details",
        ]

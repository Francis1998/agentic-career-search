"""Deterministic planning service for next job actions."""

from __future__ import annotations

from autoapply_agent.adapters.base import JobCandidate


class DeterministicPlanningService:
    """Create deterministic action plans from a job candidate."""

    def plan(self, job_candidate: JobCandidate, query: str | None) -> list[str]:
        """Build deterministic application plan steps.

        Args:
            job_candidate: Candidate to plan for.
            query: Optional run query string.

        Returns:
            Ordered plan steps.
        """

        query_hint = query.strip() if query else "target role requirements"
        company_text = job_candidate.company or "the employer"

        return [
            f"Open posting: {job_candidate.url}",
            f"Validate fit against query: {query_hint}",
            f"Tailor resume to role title: {job_candidate.title}",
            f"Draft cover note referencing {company_text}",
            "Submit application and capture confirmation details",
        ]

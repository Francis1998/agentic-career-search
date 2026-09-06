"""Deterministic application draft generator (HITL, no auto-submit).

Produces resume bullet suggestions and a short cover-note template from
job title / company / query text. This module never performs HTTP apply
actions — drafts are for human review only (SAFETY-aligned).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class ApplicationDraft:
    """Human-reviewable application draft package."""

    job_title: str
    company: str
    query: str | None
    resume_bullets: list[str]
    cover_note: str
    requires_human_review: bool = True
    auto_submit: bool = False


class ApplicationDraftService:
    """Generate deterministic, non-submitting application drafts."""

    def generate(
        self,
        *,
        job_title: str,
        company: str | None = None,
        query: str | None = None,
    ) -> ApplicationDraft:
        """Build a draft package for human-in-the-loop review.

        Args:
            job_title: Target role title.
            company: Optional company name.
            query: Optional user objective / search query.

        Returns:
            ApplicationDraft with bullets and cover note. Never submits.
        """

        company_name = (company or "the hiring team").strip() or "the hiring team"
        title = job_title.strip() or "the open role"
        focus = (query or "").strip()

        resume_bullets = self._resume_bullets(title=title, query=focus)
        cover_note = self._cover_note(title=title, company=company_name, query=focus)
        return ApplicationDraft(
            job_title=title,
            company=company_name,
            query=query,
            resume_bullets=resume_bullets,
            cover_note=cover_note,
            requires_human_review=True,
            auto_submit=False,
        )

    @staticmethod
    def _resume_bullets(*, title: str, query: str) -> list[str]:
        """Create deterministic resume bullet suggestions."""

        focus_clause = f" aligned to {query}" if query else ""
        return [
            f"Delivered outcomes relevant to {title}{focus_clause}.",
            f"Collaborated cross-functionally to ship work matching {title} expectations.",
            "Quantified impact with clear metrics and stakeholder-facing summaries.",
            "Documented decisions so reviewers can audit trade-offs and next steps.",
        ]

    @staticmethod
    def _cover_note(*, title: str, company: str, query: str) -> str:
        """Create a short cover-note template for human editing."""

        focus_line = (
            f" My search focus is {query}, which maps well to this opening." if query else ""
        )
        return (
            f"Hello {company} hiring team,\n\n"
            f"I am interested in the {title} role and would welcome a conversation "
            f"about how my recent work maps to your needs.{focus_line}\n\n"
            "I have prepared tailored resume bullets for your review and am happy "
            "to adjust emphasis before any formal submission.\n\n"
            "Thank you for your time,\n"
            "[Your Name]\n"
            "\n"
            "— Draft only: human review required; no auto-submit —"
        )

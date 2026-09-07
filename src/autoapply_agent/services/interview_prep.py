"""Deterministic interview-prep brief generator (HITL assistive only).

Builds likely questions, STAR prompts, and focus gaps from job title /
company / description text. Never contacts recruiters or schedules interviews.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_WORD_RE = re.compile(r"[a-z0-9][a-z0-9+.#/-]*", re.IGNORECASE)

_SKILL_HINTS: tuple[str, ...] = (
    "python",
    "fastapi",
    "kubernetes",
    "aws",
    "react",
    "sql",
    "distributed",
    "ml",
    "security",
    "leadership",
)


@dataclass(slots=True, frozen=True)
class InterviewPrepBrief:
    """Human-reviewable interview preparation package."""

    job_title: str
    company: str
    likely_questions: list[str]
    star_prompts: list[str]
    focus_gaps: list[str]
    requires_human_review: bool = True


class InterviewPrepBriefService:
    """Generate deterministic interview-prep briefs for HITL review."""

    def generate(
        self,
        *,
        job_title: str,
        company: str | None = None,
        job_text: str | None = None,
        candidate_skills: list[str] | None = None,
    ) -> InterviewPrepBrief:
        """Build an interview-prep brief from role context.

        Args:
            job_title: Target role title.
            company: Optional company name.
            job_text: Optional job description text.
            candidate_skills: Optional skills the candidate claims.

        Returns:
            InterviewPrepBrief with questions, STAR prompts, and gaps.
        """

        title = job_title.strip() or "the open role"
        company_name = (company or "the hiring team").strip() or "the hiring team"
        text = (job_text or "").strip()
        skills = [s.strip() for s in (candidate_skills or []) if s and s.strip()]

        likely_questions = self._likely_questions(title=title, company=company_name, job_text=text)
        star_prompts = self._star_prompts(title=title, job_text=text)
        focus_gaps = self._focus_gaps(job_text=text, candidate_skills=skills)
        return InterviewPrepBrief(
            job_title=title,
            company=company_name,
            likely_questions=likely_questions,
            star_prompts=star_prompts,
            focus_gaps=focus_gaps,
            requires_human_review=True,
        )

    @staticmethod
    def _likely_questions(*, title: str, company: str, job_text: str) -> list[str]:
        """Create deterministic likely interview questions."""

        questions = [
            f"Walk me through a project that best prepares you for a {title} role.",
            f"Why are you interested in {company} and this {title} opening?",
            f"Describe a hard trade-off you made that would matter for {title} work.",
            "Tell me about a time you recovered from a production or delivery failure.",
        ]
        lowered = job_text.lower()
        if "remote" in lowered or "distributed" in lowered:
            questions.append("How do you collaborate effectively on a distributed team?")
        if "lead" in title.lower() or "manager" in title.lower():
            questions.append("How do you coach engineers and set technical direction?")
        return questions

    @staticmethod
    def _star_prompts(*, title: str, job_text: str) -> list[str]:
        """Create STAR (Situation/Task/Action/Result) story prompts."""

        prompts = [
            f"Situation: a high-stakes delivery related to {title} responsibilities.",
            "Task: the concrete ownership boundary you accepted.",
            "Action: the steps you took, including tools and collaboration.",
            "Result: measurable impact and what you would change next time.",
        ]
        tokens = {t.lower() for t in _WORD_RE.findall(job_text)}
        for hint in _SKILL_HINTS:
            if hint in tokens:
                prompts.append(f"Bonus STAR: a story where {hint} was central to the outcome.")
                break
        return prompts

    @staticmethod
    def _focus_gaps(*, job_text: str, candidate_skills: list[str]) -> list[str]:
        """List skills hinted in the JD that the candidate did not claim."""

        if not job_text:
            return ["Review the full job description for unstated expectations."]
        tokens = {t.lower() for t in _WORD_RE.findall(job_text)}
        claimed = {s.strip().lower() for s in candidate_skills}
        gaps = [hint for hint in _SKILL_HINTS if hint in tokens and hint not in claimed]
        if not gaps:
            return ["No major keyword gaps detected in the assistive hint list."]
        return [f"Prepare talking points for: {gap}" for gap in gaps]

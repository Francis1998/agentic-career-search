"""Skills-profile fit scoring helpers.

Given a candidate skill list and job text, compute a fit score in ``[0.0, 1.0]``
plus matched / missing skill lists. Pure function API — no database required
for v1. Case-insensitive token matching.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_WORD_RE = re.compile(r"[a-z0-9][a-z0-9+.#/-]*", re.IGNORECASE)


@dataclass(slots=True, frozen=True)
class SkillsFitResult:
    """Outcome of comparing candidate skills to job text."""

    fit_score: float
    matched_skills: list[str]
    missing_skills: list[str]


def normalize_skill(skill: str) -> str:
    """Normalize a skill token for case-insensitive comparison.

    Args:
        skill: Raw skill string.

    Returns:
        Lowercased trimmed skill token.
    """

    return skill.strip().lower()


def extract_job_tokens(job_text: str) -> set[str]:
    """Extract normalized word tokens from job text.

    Args:
        job_text: Free-form job description / title text.

    Returns:
        Set of lowercased tokens found in the text.
    """

    return {token.lower() for token in _WORD_RE.findall(job_text or "")}


def score_skills_fit(
    candidate_skills: list[str] | None,
    job_text: str | None,
) -> SkillsFitResult:
    """Score how well candidate skills match job text.

    Matching is case-insensitive whole-token containment of each candidate
    skill within the job text token set. Multi-word skills match when every
    word of the skill appears in the job tokens.

    Args:
        candidate_skills: Skills claimed by the candidate.
        job_text: Job title and/or description text.

    Returns:
        SkillsFitResult with fit_score in [0.0, 1.0], matched, and missing.
        Empty candidate skills yields fit_score 0.0.
    """

    skills = [s for s in (candidate_skills or []) if s and s.strip()]
    if not skills:
        return SkillsFitResult(fit_score=0.0, matched_skills=[], missing_skills=[])

    job_tokens = extract_job_tokens(job_text or "")
    matched: list[str] = []
    missing: list[str] = []

    for skill in skills:
        normalized = normalize_skill(skill)
        skill_words = [w for w in _WORD_RE.findall(normalized)]
        if skill_words and all(word in job_tokens for word in skill_words):
            matched.append(skill.strip())
        else:
            missing.append(skill.strip())

    fit_score = round(len(matched) / len(skills), 4)
    return SkillsFitResult(
        fit_score=fit_score,
        matched_skills=matched,
        missing_skills=missing,
    )


class SkillsProfileFitScorer:
    """Callable wrapper around :func:`score_skills_fit` for service-style use."""

    def score(
        self,
        candidate_skills: list[str] | None,
        job_text: str | None,
    ) -> SkillsFitResult:
        """Score candidate skills against job text.

        Args:
            candidate_skills: Skills claimed by the candidate.
            job_text: Job title and/or description text.

        Returns:
            SkillsFitResult with fit_score, matched_skills, missing_skills.
        """

        return score_skills_fit(candidate_skills, job_text)

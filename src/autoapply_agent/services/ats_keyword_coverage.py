"""ATS-style keyword coverage scoring (resume text ↔ job description).

Distinct from ``SkillsProfileFitScorer`` which matches a candidate *skills
list* against job tokens. This scorer extracts high-signal keywords from the
job description and measures how many appear in free-form resume text — the
classic ATS keyword-coverage loop used by Teal / Jobscan-style tools, exposed
as a library API for agentic triage.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

_WORD_RE = re.compile(r"[a-z][a-z0-9+.#/-]{1,}", re.IGNORECASE)

_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "has",
        "have",
        "in",
        "is",
        "it",
        "its",
        "of",
        "on",
        "or",
        "our",
        "that",
        "the",
        "their",
        "this",
        "to",
        "we",
        "with",
        "you",
        "your",
        "will",
        "can",
        "able",
        "about",
        "into",
        "over",
        "such",
        "than",
        "then",
        "them",
        "they",
        "was",
        "were",
        "what",
        "when",
        "who",
        "which",
        "while",
        "also",
        "both",
        "each",
        "more",
        "most",
        "other",
        "some",
        "team",
        "work",
        "role",
        "job",
        "years",
        "year",
        "experience",
        "including",
        "using",
        "across",
        "within",
        "required",
        "requirements",
        "preferred",
        "responsibilities",
        "opportunity",
        "position",
        "candidate",
        "candidates",
        "strong",
        "good",
        "great",
        "well",
        "must",
        "should",
        "may",
        "etc",
    }
)

_DEFAULT_TOP_K = 25


@dataclass(slots=True, frozen=True)
class KeywordCoverageResult:
    """ATS-style keyword coverage outcome."""

    coverage_score: float
    jd_keywords: list[str]
    present_keywords: list[str]
    missing_keywords: list[str]


def tokenize(text: str) -> list[str]:
    """Extract lowercased content tokens from free-form text.

    Args:
        text: Resume or job-description text.

    Returns:
        List of normalized tokens (stopwords removed).
    """

    tokens = [match.group(0).lower() for match in _WORD_RE.finditer(text or "")]
    return [token for token in tokens if token not in _STOPWORDS and len(token) > 1]


def extract_jd_keywords(job_text: str, *, top_k: int = _DEFAULT_TOP_K) -> list[str]:
    """Extract ranked keywords from a job description.

    Ranking is by term frequency; ties keep first-seen order.

    Args:
        job_text: Job title and/or description.
        top_k: Maximum keywords to return.

    Returns:
        Ordered list of distinctive JD keywords (most frequent first).
    """

    if top_k < 1:
        raise ValueError(f"top_k must be >= 1, got {top_k}")
    tokens = tokenize(job_text)
    if not tokens:
        return []
    counts = Counter(tokens)
    # Stable: sort by (-count, first-seen index)
    seen: dict[str, int] = {}
    for index, token in enumerate(tokens):
        if token not in seen:
            seen[token] = index
    ranked = sorted(counts.keys(), key=lambda token: (-counts[token], seen[token]))
    return ranked[:top_k]


def score_keyword_coverage(
    resume_text: str | None,
    job_text: str | None,
    *,
    top_k: int = _DEFAULT_TOP_K,
) -> KeywordCoverageResult:
    """Score ATS-style keyword coverage of resume against JD.

    Args:
        resume_text: Free-form resume / profile text.
        job_text: Job description text.
        top_k: Max JD keywords to evaluate.

    Returns:
        KeywordCoverageResult with coverage_score in ``[0.0, 1.0]``.
        Empty JD keywords yields coverage_score 0.0.
    """

    jd_keywords = extract_jd_keywords(job_text or "", top_k=top_k)
    if not jd_keywords:
        return KeywordCoverageResult(
            coverage_score=0.0,
            jd_keywords=[],
            present_keywords=[],
            missing_keywords=[],
        )

    resume_tokens = set(tokenize(resume_text or ""))
    present = [keyword for keyword in jd_keywords if keyword in resume_tokens]
    missing = [keyword for keyword in jd_keywords if keyword not in resume_tokens]
    coverage = round(len(present) / len(jd_keywords), 4)
    return KeywordCoverageResult(
        coverage_score=coverage,
        jd_keywords=jd_keywords,
        present_keywords=present,
        missing_keywords=missing,
    )


class AtsKeywordCoverageScorer:
    """Service-style wrapper around :func:`score_keyword_coverage`."""

    def __init__(self, *, top_k: int = _DEFAULT_TOP_K) -> None:
        """Initialize the scorer.

        Args:
            top_k: Max JD keywords considered per score call.

        Raises:
            ValueError: If top_k < 1.
        """

        if top_k < 1:
            raise ValueError(f"top_k must be >= 1, got {top_k}")
        self._top_k = top_k

    @property
    def top_k(self) -> int:
        """Return configured top_k."""

        return self._top_k

    def score(
        self,
        resume_text: str | None,
        job_text: str | None,
    ) -> KeywordCoverageResult:
        """Score resume keyword coverage against a job description.

        Args:
            resume_text: Free-form resume text.
            job_text: Job description text.

        Returns:
            KeywordCoverageResult with coverage_score and keyword lists.
        """

        return score_keyword_coverage(resume_text, job_text, top_k=self._top_k)

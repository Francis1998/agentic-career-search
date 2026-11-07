"""Deterministic scoring service for job relevance."""

from __future__ import annotations

import re
from dataclasses import dataclass
from hashlib import sha256

from autoapply_agent.adapters.base import JobCandidate

_WORD_PATTERN = re.compile(r"[a-z0-9]+")

BASE_SCORE = 0.45
"""Baseline relevance every captured candidate starts from."""
KEYWORD_BONUS_PER_TERM = 0.1
"""Bonus per distinct query term matched as a whole word."""
KEYWORD_BONUS_CAP = 0.4
"""Upper bound of the keyword bonus."""
STABILITY_BONUS_MAX = 0.1
"""Upper bound of the URL-hash tiebreaker."""
MAX_SCORE = 0.99
"""Cap applied to the summed score."""


@dataclass(slots=True, frozen=True)
class ScoreBreakdown:
    """Additive components of one deterministic score.

    Attributes:
        query_terms: Normalized distinct query terms, sorted.
        matched_terms: Query terms found as whole words in title, location or company.
        base: Baseline relevance (:data:`BASE_SCORE`).
        keyword_bonus: :data:`KEYWORD_BONUS_PER_TERM` per matched term, capped at
            :data:`KEYWORD_BONUS_CAP`.
        stability_bonus: Tiebreaker in ``[0, STABILITY_BONUS_MAX]`` derived from a hash
            of the posting URL; it keeps orderings stable and is not a fit signal.
        capped: Whether the sum exceeded :data:`MAX_SCORE`.
        score: The capped sum rounded to 4 decimals, as returned by
            :meth:`DeterministicScoringService.score`.
    """

    query_terms: tuple[str, ...]
    matched_terms: tuple[str, ...]
    base: float
    keyword_bonus: float
    stability_bonus: float
    capped: bool
    score: float


class DeterministicScoringService:
    """Compute deterministic relevance score for a job candidate."""

    def score(self, job_candidate: JobCandidate, query: str | None) -> float:
        """Score a job candidate using deterministic heuristics.

        Args:
            job_candidate: Candidate to score.
            query: Optional user query text.

        Returns:
            Deterministic score in range [0.0, 1.0].
        """

        return self.breakdown(job_candidate, query).score

    def breakdown(self, job_candidate: JobCandidate, query: str | None) -> ScoreBreakdown:
        """Score a job candidate and return every component of the score.

        Args:
            job_candidate: Candidate to score.
            query: Optional user query text.

        Returns:
            Score components; ``score`` equals :meth:`score` for the same inputs.
        """

        matched_terms = self.match_terms(job_candidate, query)
        keyword_bonus = min(len(matched_terms) * KEYWORD_BONUS_PER_TERM, KEYWORD_BONUS_CAP)

        digest_prefix = sha256(job_candidate.url.encode("utf-8")).hexdigest()[:8]
        digest_component = int(digest_prefix, 16) / 0xFFFFFFFF
        stability_bonus = STABILITY_BONUS_MAX * digest_component

        total = BASE_SCORE + keyword_bonus + stability_bonus
        final_score = min(MAX_SCORE, total)
        return ScoreBreakdown(
            query_terms=tuple(self._tokenize(query)),
            matched_terms=tuple(matched_terms),
            base=BASE_SCORE,
            keyword_bonus=keyword_bonus,
            stability_bonus=stability_bonus,
            capped=total > MAX_SCORE,
            score=round(final_score, 4),
        )

    def match_terms(self, job_candidate: JobCandidate, query: str | None) -> list[str]:
        """Return normalized query terms matched in candidate search text.

        Args:
            job_candidate: Candidate to inspect.
            query: Optional query text.

        Returns:
            Sorted list of matched query terms.
        """

        normalized_query_tokens = self._tokenize(query)
        searchable_text = " ".join(
            token
            for token in [
                job_candidate.title,
                job_candidate.location or "",
                job_candidate.company or "",
            ]
            if token
        ).lower()
        searchable_words = set(_WORD_PATTERN.findall(searchable_text))
        return [token for token in normalized_query_tokens if token in searchable_words]

    @staticmethod
    def _tokenize(query: str | None) -> list[str]:
        """Tokenize query text into normalized distinct terms.

        Args:
            query: Optional search query.

        Returns:
            List of normalized tokens.
        """

        if not query:
            return []
        tokens = _WORD_PATTERN.findall(query.lower())
        return sorted(set(tokens))

"""Deterministic scoring service for job relevance."""

from __future__ import annotations

import re
from hashlib import sha256

from autoapply_agent.adapters.base import JobCandidate

_WORD_PATTERN = re.compile(r"[a-z0-9]+")


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

        matched_terms = self.match_terms(job_candidate, query)
        keyword_bonus = min(len(matched_terms) * 0.1, 0.4)

        digest_prefix = sha256(job_candidate.url.encode("utf-8")).hexdigest()[:8]
        digest_component = int(digest_prefix, 16) / 0xFFFFFFFF
        stability_bonus = 0.1 * digest_component

        base_score = 0.45
        final_score = min(0.99, base_score + keyword_bonus + stability_bonus)
        return round(final_score, 4)

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

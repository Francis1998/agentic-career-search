"""Cross-source fuzzy job deduplication.

URL-only dedup misses the same role mirrored across Indeed, LinkedIn, and
Greenhouse with different URLs. This module clusters near-duplicate
title+company pairs with ``difflib`` after an exact-URL pass — inspired by
JobSpy / Teal triage gaps without pulling in heavy fuzzy libraries.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Protocol

_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")
_DEFAULT_THRESHOLD = 0.88


class JobLike(Protocol):
    """Minimal job shape required for cross-source dedup."""

    title: str
    company: str | None
    url: str


@dataclass(slots=True, frozen=True)
class DedupCluster:
    """One cluster of near-duplicate job postings."""

    canonical_index: int
    member_indices: tuple[int, ...]
    similarity: float


@dataclass(slots=True, frozen=True)
class DedupResult:
    """Outcome of cross-source deduplication."""

    kept_indices: tuple[int, ...]
    clusters: tuple[DedupCluster, ...]
    dropped_count: int


def normalize_title(title: str) -> str:
    """Normalize a job title for fuzzy comparison.

    Args:
        title: Raw job title.

    Returns:
        Lowercased alphanumeric-collapsed title string.
    """

    collapsed = _NON_ALNUM_RE.sub(" ", (title or "").strip().lower())
    return " ".join(collapsed.split())


def normalize_company(company: str | None) -> str:
    """Normalize a company name for fuzzy comparison.

    Args:
        company: Raw company string or None.

    Returns:
        Lowercased alphanumeric-collapsed company string (empty if missing).
    """

    if not company:
        return ""
    collapsed = _NON_ALNUM_RE.sub(" ", company.strip().lower())
    # Drop common legal suffixes that inflate false mismatches.
    tokens = [
        token
        for token in collapsed.split()
        if token not in {"inc", "llc", "ltd", "corp", "co", "gmbh", "plc"}
    ]
    return " ".join(tokens)


def title_company_key(title: str, company: str | None) -> str:
    """Build a composite key for similarity scoring.

    Args:
        title: Job title.
        company: Company name.

    Returns:
        ``"{title}|{company}"`` normalized composite key.
    """

    return f"{normalize_title(title)}|{normalize_company(company)}"


def similarity(left: str, right: str) -> float:
    """Compute SequenceMatcher ratio between two strings.

    Args:
        left: First normalized string.
        right: Second normalized string.

    Returns:
        Similarity in ``[0.0, 1.0]``.
    """

    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0
    return round(SequenceMatcher(None, left, right).ratio(), 4)


class CrossSourceJobDeduper:
    """Deduplicate jobs across sources via URL then fuzzy title+company."""

    def __init__(self, *, threshold: float = _DEFAULT_THRESHOLD) -> None:
        """Initialize the deduper.

        Args:
            threshold: Minimum title+company similarity to treat as duplicate.
                Must be in ``(0.0, 1.0]``.

        Raises:
            ValueError: If threshold is out of range.
        """

        if not 0.0 < threshold <= 1.0:
            raise ValueError(f"threshold must be in (0.0, 1.0], got {threshold}")
        self._threshold = threshold

    @property
    def threshold(self) -> float:
        """Return the configured similarity threshold."""

        return self._threshold

    def dedupe(self, jobs: Sequence[JobLike]) -> DedupResult:
        """Keep first occurrence of each unique job; cluster near-duplicates.

        Pass 1 drops exact URL duplicates (case-insensitive). Pass 2 clusters
        remaining jobs whose normalized title+company keys exceed
        ``threshold``. The earliest index in each cluster is the canonical
        kept member.

        Args:
            jobs: Sequence of job-like objects with title/company/url.

        Returns:
            DedupResult with kept indices, clusters, and dropped count.
        """

        if not jobs:
            return DedupResult(kept_indices=(), clusters=(), dropped_count=0)

        # Pass 1: exact URL
        url_seen: dict[str, int] = {}
        after_url: list[int] = []
        for index, job in enumerate(jobs):
            url_key = (job.url or "").strip().lower()
            if url_key and url_key in url_seen:
                continue
            if url_key:
                url_seen[url_key] = index
            after_url.append(index)

        # Pass 2: fuzzy title+company among URL survivors
        parent: dict[int, int] = {index: index for index in after_url}
        best_sim: dict[int, float] = {index: 1.0 for index in after_url}
        keys = {
            index: title_company_key(jobs[index].title, jobs[index].company) for index in after_url
        }

        for position, index in enumerate(after_url):
            for prior in after_url[:position]:
                root_prior = self._find(parent, prior)
                root_index = self._find(parent, index)
                if root_prior == root_index:
                    continue
                score = similarity(keys[index], keys[prior])
                if score >= self._threshold:
                    # Union into earlier root
                    if root_prior < root_index:
                        parent[root_index] = root_prior
                        best_sim[root_prior] = min(best_sim.get(root_prior, 1.0), score)
                    else:
                        parent[root_prior] = root_index
                        best_sim[root_index] = min(best_sim.get(root_index, 1.0), score)

        clusters_map: dict[int, list[int]] = {}
        for index in after_url:
            root = self._find(parent, index)
            clusters_map.setdefault(root, []).append(index)

        clusters: list[DedupCluster] = []
        kept: list[int] = []
        for root, members in sorted(clusters_map.items(), key=lambda item: item[0]):
            members_sorted = tuple(sorted(members))
            clusters.append(
                DedupCluster(
                    canonical_index=root,
                    member_indices=members_sorted,
                    similarity=best_sim.get(root, 1.0) if len(members_sorted) > 1 else 1.0,
                )
            )
            kept.append(root)

        dropped = len(jobs) - len(kept)
        return DedupResult(
            kept_indices=tuple(sorted(kept)),
            clusters=tuple(clusters),
            dropped_count=dropped,
        )

    def keep(self, jobs: Sequence[JobLike]) -> list[JobLike]:
        """Return canonical jobs after deduplication (stable order).

        Args:
            jobs: Sequence of job-like objects.

        Returns:
            List of kept jobs in ascending original index order.
        """

        result = self.dedupe(jobs)
        return [jobs[index] for index in result.kept_indices]

    @staticmethod
    def _find(parent: dict[int, int], index: int) -> int:
        """Path-compressed find for union-find clustering."""

        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

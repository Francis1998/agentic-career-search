"""Location / remote preference fit scorer vs a job posting.

Closes the gap vs RemoteOK / WeWorkRemotely preference filters by scoring
candidate geo + remote prefs against a posting's location and remote policy.
Pure heuristic API — no network I/O.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_WORD_RE = re.compile(r"[a-z0-9][a-z0-9+.#/-]*", re.IGNORECASE)

_REMOTE_TOKENS = frozenset(
    {
        "remote",
        "distributed",
        "anywhere",
        "wfh",
        "workfromhome",
        "fully-remote",
        "fullyremote",
    }
)


@dataclass(slots=True, frozen=True)
class LocationRemoteFitResult:
    """Outcome of scoring location/remote preference fit."""

    fit_score: float
    reasons: list[str]


def _normalize_tokens(text: str | None) -> set[str]:
    """Extract lowercased word tokens from free-form text."""

    return {token.lower() for token in _WORD_RE.findall(text or "")}


def _is_remote_policy(policy: str | None) -> bool:
    """Return True when policy text signals remote-friendly work."""

    tokens = _normalize_tokens(policy)
    lowered = (policy or "").strip().lower()
    if any(token in tokens for token in _REMOTE_TOKENS):
        return True
    return any(needle in lowered for needle in ("fully remote", "work from home", "remote-first"))


def _geo_overlap(candidate_locations: list[str] | None, posting_location: str | None) -> bool:
    """True when any candidate location token overlaps the posting location."""

    posting_tokens = _normalize_tokens(posting_location)
    if not posting_tokens:
        return False
    for location in candidate_locations or []:
        candidate_tokens = _normalize_tokens(location)
        if candidate_tokens and candidate_tokens & posting_tokens:
            return True
    return False


class LocationRemoteFitScorer:
    """Score candidate geo/remote prefs against a posting."""

    def score(
        self,
        *,
        candidate_locations: list[str] | None,
        prefers_remote: bool,
        posting_location: str | None,
        posting_remote_policy: str | None,
    ) -> LocationRemoteFitResult:
        """Compute a fit score in ``[0.0, 1.0]`` with human-readable reasons.

        Args:
            candidate_locations: Locations the candidate can work from.
            prefers_remote: Whether the candidate prefers remote work.
            posting_location: Location string from the job posting.
            posting_remote_policy: Remote / hybrid / onsite policy text.

        Returns:
            LocationRemoteFitResult with ``fit_score`` clamped to [0, 1]
            and explanatory ``reasons``. Blank inputs yield a low score.
        """

        locations = [loc for loc in (candidate_locations or []) if loc and str(loc).strip()]
        posting_loc = (posting_location or "").strip()
        policy = (posting_remote_policy or "").strip()

        reasons: list[str] = []
        score = 0.0

        if not locations and not posting_loc and not policy:
            return LocationRemoteFitResult(
                fit_score=0.0,
                reasons=[
                    "Blank inputs: no candidate locations, posting location, or remote policy."
                ],
            )

        remote_friendly = _is_remote_policy(policy) or _is_remote_policy(posting_loc)
        geo_match = _geo_overlap(locations, posting_loc)

        if prefers_remote and remote_friendly:
            score += 0.6
            reasons.append("Remote preference matches posting remote-friendly policy.")
        elif prefers_remote and not remote_friendly:
            score += 0.1
            reasons.append("Candidate prefers remote but posting is not remote-friendly.")
        elif not prefers_remote and remote_friendly:
            score += 0.35
            reasons.append("Posting is remote-friendly; candidate did not require remote.")
        else:
            score += 0.2
            reasons.append("Neither side strongly signals remote; relying on geo overlap.")

        if geo_match:
            score += 0.4
            reasons.append("Candidate location overlaps posting location tokens.")
        elif locations and posting_loc:
            reasons.append("Geo mismatch: candidate locations do not overlap posting location.")
        elif not locations:
            reasons.append("No candidate locations provided; geo component skipped.")
        elif not posting_loc:
            reasons.append("No posting location provided; geo component skipped.")

        fit_score = round(min(1.0, max(0.0, score)), 4)
        return LocationRemoteFitResult(fit_score=fit_score, reasons=reasons)

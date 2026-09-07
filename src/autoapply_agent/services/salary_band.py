"""Deterministic USD salary-band estimator (assistive, non-authoritative).

Estimates a low/mid/high compensation band from job title level tokens and
location / remote heuristics. Pure function API — no market API calls.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_WORD_RE = re.compile(r"[a-z0-9][a-z0-9+.#/-]*", re.IGNORECASE)

_BASE_MID = {
    "intern": 70_000,
    "junior": 95_000,
    "mid": 130_000,
    "senior": 175_000,
    "staff": 220_000,
    "principal": 260_000,
    "unknown": 140_000,
}

_LEVEL_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("intern", ("intern", "internship")),
    ("junior", ("junior", "entry", "associate", "new-grad", "newgrad")),
    ("senior", ("senior", "sr")),
    ("staff", ("staff",)),
    ("principal", ("principal", "distinguished", "fellow")),
    ("mid", ("mid", "mid-level", "intermediate")),
)


@dataclass(slots=True, frozen=True)
class SalaryBandEstimate:
    """Assistive USD compensation band estimate."""

    currency: str
    low: int
    mid: int
    high: int
    level: str
    location_factor: float
    rationale: list[str]
    confidence: float


def parse_level_from_title(title: str) -> str:
    """Infer a coarse seniority level from a job title.

    Args:
        title: Raw job title.

    Returns:
        One of intern/junior/mid/senior/staff/principal/unknown.
    """

    tokens = {t.lower() for t in _WORD_RE.findall(title or "")}
    lowered = (title or "").lower()
    for level, patterns in _LEVEL_PATTERNS:
        for pattern in patterns:
            if pattern in tokens or pattern in lowered:
                return level
    return "unknown"


def _location_factor(location: str | None, job_text: str | None) -> tuple[float, str]:
    """Return a location multiplier and rationale fragment."""

    blob = f"{location or ''} {job_text or ''}".lower()
    if any(
        token in blob
        for token in ("san francisco", "sf bay", "bay area", "nyc", "new york", "seattle")
    ):
        return 1.25, "High-cost metro token detected (+25%)."
    if any(token in blob for token in ("london", "zurich", "singapore", "sydney")):
        return 1.15, "Global high-cost metro token detected (+15%)."
    if "remote" in blob or "anywhere" in blob:
        return 1.05, "Remote/anywhere token detected (+5%)."
    if any(token in blob for token in ("midwest", "south", "texas", "ohio", "india", "latam")):
        return 0.9, "Lower-cost region token detected (-10%)."
    return 1.0, "No strong location signal; using baseline factor."


class SalaryBandEstimator:
    """Estimate a USD salary band from title/location heuristics."""

    def estimate(
        self,
        *,
        job_title: str,
        location: str | None = None,
        job_text: str | None = None,
    ) -> SalaryBandEstimate:
        """Estimate a low/mid/high USD band for a role.

        Args:
            job_title: Target role title.
            location: Optional location string.
            job_text: Optional job description text.

        Returns:
            SalaryBandEstimate with currency USD and confidence in [0.0, 1.0].
        """

        title = (job_title or "").strip() or "unknown role"
        level = parse_level_from_title(title)
        mid_base = _BASE_MID[level]
        factor, location_note = _location_factor(location, job_text)
        mid = int(round(mid_base * factor, -3))
        low = int(round(mid * 0.85, -3))
        high = int(round(mid * 1.15, -3))
        confidence = 0.55 if level != "unknown" else 0.35
        if location or (
            job_text and any(t in (job_text or "").lower() for t in ("remote", "sf", "nyc"))
        ):
            confidence = min(0.85, confidence + 0.15)
        rationale = [
            f"Parsed seniority level: {level}.",
            f"Baseline mid for level: ${mid_base:,}.",
            location_note,
            "Band width is ±15% around adjusted mid (assistive only).",
        ]
        return SalaryBandEstimate(
            currency="USD",
            low=low,
            mid=mid,
            high=high,
            level=level,
            location_factor=factor,
            rationale=rationale,
            confidence=round(confidence, 2),
        )

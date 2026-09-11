"""HITL portfolio↔JD theme matcher (offline bullet → theme mapping).

Closes the gap vs Teal/Jobscan portfolio↔JD mapping UIs that leave candidates
to hand-align project bullets to posting themes. This matcher only scores
offline token overlap for human review — it never rewrites portfolios, never
auto-applies, and never performs network I/O.

Distinct from ``AtsKeywordCoverageScorer`` (resume free text ↔ JD keywords) and
``SkillsProfileFitScorer`` (skills list ↔ job tokens).

Optional later polish via GPT-5.5 / Claude Sonnet 4.6 / Gemini 3.x / Kimi K2
must stay advisory.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_WORD_RE = re.compile(r"[a-z0-9][a-z0-9+.#/-]*", re.IGNORECASE)


@dataclass(slots=True, frozen=True)
class PortfolioMatchResult:
    """Human-reviewable portfolio bullet match for one JD theme."""

    jd_theme: str
    matched_bullets: list[str]
    score: float
    requires_human_review: bool


class PortfolioProjectMatcher:
    """Map portfolio bullets to JD theme keywords via offline token overlap."""

    def match(
        self,
        *,
        portfolio_bullets: list[str],
        jd_themes: list[str],
    ) -> list[PortfolioMatchResult]:
        """Score portfolio bullets against each JD theme (HITL; no network).

        Args:
            portfolio_bullets: Project / experience bullet strings (required).
            jd_themes: JD theme keyword phrases to match against (required).

        Returns:
            One ``PortfolioMatchResult`` per non-blank theme, each with
            ``requires_human_review=True`` and ``score`` in ``[0.0, 1.0]``.

        Raises:
            ValueError: If themes or bullets are blank / empty after trim.
        """

        cleaned_bullets = _require_nonblank_list(
            portfolio_bullets,
            field="portfolio_bullets",
        )
        cleaned_themes = _require_nonblank_list(jd_themes, field="jd_themes")

        results: list[PortfolioMatchResult] = []
        for theme in cleaned_themes:
            theme_tokens = _tokenize(theme)
            if not theme_tokens:
                raise ValueError("jd_themes must contain at least one tokenizable theme")

            matched: list[str] = []
            best = 0.0
            for bullet in cleaned_bullets:
                bullet_tokens = _tokenize(bullet)
                if not bullet_tokens:
                    continue
                overlap = theme_tokens & bullet_tokens
                if not overlap:
                    continue
                bullet_score = len(overlap) / len(theme_tokens)
                matched.append(bullet)
                if bullet_score > best:
                    best = bullet_score

            results.append(
                PortfolioMatchResult(
                    jd_theme=theme,
                    matched_bullets=matched,
                    score=round(best, 4),
                    requires_human_review=True,
                )
            )
        return results


def _require_nonblank_list(values: list[str] | None, *, field: str) -> list[str]:
    if values is None:
        raise ValueError(f"{field} must contain at least one non-empty string")
    cleaned = [item.strip() for item in values if item and str(item).strip()]
    if not cleaned:
        raise ValueError(f"{field} must contain at least one non-empty string")
    return cleaned


def _tokenize(text: str) -> set[str]:
    return {token.lower() for token in _WORD_RE.findall(text or "")}

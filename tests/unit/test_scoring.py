"""Unit tests for deterministic scoring service."""

from __future__ import annotations

from typing import TYPE_CHECKING

from autoapply_agent.adapters.base import JobCandidate
from autoapply_agent.services.scoring import (
    BASE_SCORE,
    KEYWORD_BONUS_CAP,
    KEYWORD_BONUS_PER_TERM,
    STABILITY_BONUS_MAX,
    DeterministicScoringService,
)

if TYPE_CHECKING:
    from _pytest.capture import CaptureFixture
    from _pytest.fixtures import FixtureRequest
    from _pytest.logging import LogCaptureFixture
    from _pytest.monkeypatch import MonkeyPatch
    from pytest_mock.plugin import MockerFixture


def test_score_is_deterministic_for_same_job() -> None:
    """Score should remain stable across repeated calls."""

    scoring_service = DeterministicScoringService()
    candidate = JobCandidate(
        external_id="123",
        title="Python Backend Engineer",
        location="Remote",
        company="example.com",
        url="https://example.com/jobs/123",
        raw={"source": "unit"},
    )

    first_score = scoring_service.score(candidate, "python backend")
    second_score = scoring_service.score(candidate, "python backend")

    assert first_score == second_score


def test_query_tokens_increase_score() -> None:
    """Matching query terms should produce higher score than unmatched terms."""

    scoring_service = DeterministicScoringService()
    candidate = JobCandidate(
        external_id="abc",
        title="Senior Data Engineer",
        location="New York",
        company="example.org",
        url="https://example.org/jobs/abc",
        raw=None,
    )

    unmatched_score = scoring_service.score(candidate, "frontend swift ios")
    matched_score = scoring_service.score(candidate, "data engineer")

    assert matched_score > unmatched_score


def test_match_terms_uses_word_boundaries() -> None:
    """A query term must match a whole word, not an arbitrary substring."""

    scoring_service = DeterministicScoringService()
    candidate = JobCandidate(
        external_id="js-1",
        title="Senior JavaScript Engineer",
        location="Remote",
        company="example.com",
        url="https://example.com/jobs/js-1",
        raw=None,
    )

    matched_terms = scoring_service.match_terms(candidate, "java")

    assert matched_terms == []


def test_match_terms_matches_distinct_words() -> None:
    """Whole-word query terms present in the candidate text should match."""

    scoring_service = DeterministicScoringService()
    candidate = JobCandidate(
        external_id="js-2",
        title="Senior JavaScript Engineer",
        location="Remote",
        company="example.com",
        url="https://example.com/jobs/js-2",
        raw=None,
    )

    matched_terms = scoring_service.match_terms(candidate, "javascript engineer")

    assert matched_terms == ["engineer", "javascript"]


def test_match_terms_normalizes_query_punctuation() -> None:
    """Punctuation attached to query terms must not defeat matching."""

    scoring_service = DeterministicScoringService()
    candidate = JobCandidate(
        external_id="js-3",
        title="Senior JavaScript Engineer",
        location="Remote",
        company="example.com",
        url="https://example.com/jobs/js-3",
        raw=None,
    )

    matched_terms = scoring_service.match_terms(candidate, "javascript, engineer!")

    assert matched_terms == ["engineer", "javascript"]


def test_match_terms_splits_compound_query_tokens() -> None:
    """Compound query tokens should split on non-word characters before matching."""

    scoring_service = DeterministicScoringService()
    candidate = JobCandidate(
        external_id="js-4",
        title="Senior Data Engineer",
        location="Remote",
        company="example.com",
        url="https://example.com/jobs/js-4",
        raw=None,
    )

    matched_terms = scoring_service.match_terms(candidate, "data-engineer")

    assert matched_terms == ["data", "engineer"]


def test_breakdown_components_add_up_to_the_score() -> None:
    """The breakdown exposes the exact parts ``score`` sums, capped and rounded."""

    scoring_service = DeterministicScoringService()
    candidate = JobCandidate(
        external_id="bd-1",
        title="Senior Python Backend Engineer",
        location="Remote - US",
        company="Acme Robotics",
        url="https://boards.greenhouse.io/acme/jobs/4101",
        raw=None,
    )

    breakdown = scoring_service.breakdown(candidate, "Python, backend remote golang")

    assert breakdown.query_terms == ("backend", "golang", "python", "remote")
    assert breakdown.matched_terms == ("backend", "python", "remote")
    assert breakdown.base == BASE_SCORE
    assert breakdown.keyword_bonus == 3 * KEYWORD_BONUS_PER_TERM
    assert 0 <= breakdown.stability_bonus <= STABILITY_BONUS_MAX
    assert breakdown.capped is False
    assert breakdown.score == scoring_service.score(candidate, "Python, backend remote golang")
    assert breakdown.score == round(
        breakdown.base + breakdown.keyword_bonus + breakdown.stability_bonus, 4
    )


def test_breakdown_caps_the_keyword_bonus_and_handles_missing_queries() -> None:
    """Five matched terms still earn the capped bonus; no query earns none."""

    scoring_service = DeterministicScoringService()
    candidate = JobCandidate(
        external_id="bd-2",
        title="Senior Staff Python Backend Platform Engineer",
        location=None,
        company=None,
        url="https://example.com/jobs/bd-2",
        raw=None,
    )

    capped = scoring_service.breakdown(candidate, "senior staff python backend platform")
    no_query = scoring_service.breakdown(candidate, None)

    assert len(capped.matched_terms) == 5
    assert capped.keyword_bonus == KEYWORD_BONUS_CAP
    assert no_query.query_terms == no_query.matched_terms == ()
    assert no_query.keyword_bonus == 0
    assert no_query.score == scoring_service.score(candidate, None)

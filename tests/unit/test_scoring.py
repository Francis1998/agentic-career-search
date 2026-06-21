"""Unit tests for deterministic scoring service."""

from __future__ import annotations

from typing import TYPE_CHECKING

from autoapply_agent.adapters.base import JobCandidate
from autoapply_agent.services.scoring import DeterministicScoringService

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

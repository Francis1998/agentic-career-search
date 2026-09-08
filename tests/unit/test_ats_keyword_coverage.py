"""Unit tests for AtsKeywordCoverageScorer / score_keyword_coverage."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from autoapply_agent.services.ats_keyword_coverage import (
    AtsKeywordCoverageScorer,
    extract_jd_keywords,
    score_keyword_coverage,
)

if TYPE_CHECKING:
    from _pytest.capture import CaptureFixture
    from _pytest.fixtures import FixtureRequest
    from _pytest.logging import LogCaptureFixture
    from _pytest.monkeypatch import MonkeyPatch
    from pytest_mock.plugin import MockerFixture


def test_empty_jd_yields_zero_coverage() -> None:
    """Empty job text returns coverage_score 0.0."""

    result = score_keyword_coverage("Python FastAPI engineer", "")
    assert result.coverage_score == 0.0
    assert result.jd_keywords == []
    assert result.present_keywords == []
    assert result.missing_keywords == []


def test_full_coverage() -> None:
    """Resume containing all JD keywords scores 1.0."""

    jd = "Python FastAPI Kubernetes"
    resume = "Built Python FastAPI services on Kubernetes"
    result = score_keyword_coverage(resume, jd, top_k=10)
    assert "python" in result.jd_keywords
    assert result.coverage_score == 1.0
    assert result.missing_keywords == []


def test_partial_coverage() -> None:
    """Partial keyword overlap yields fractional coverage."""

    jd = "Python Kubernetes Terraform Go"
    resume = "Senior Python developer with Terraform"
    result = score_keyword_coverage(resume, jd, top_k=10)
    assert "python" in result.present_keywords
    assert "terraform" in result.present_keywords
    assert "kubernetes" in result.missing_keywords
    assert 0.0 < result.coverage_score < 1.0


def test_stopwords_excluded_from_jd_keywords() -> None:
    """Common stopwords are not treated as ATS keywords."""

    keywords = extract_jd_keywords("The role is for the team with experience", top_k=10)
    assert "the" not in keywords
    assert "role" not in keywords
    assert "experience" not in keywords


def test_case_insensitive() -> None:
    """Matching is case-insensitive."""

    result = score_keyword_coverage("PYTHON fastapi", "Python FastAPI", top_k=5)
    assert result.coverage_score == 1.0


def test_scorer_class_delegates() -> None:
    """AtsKeywordCoverageScorer.score mirrors the pure function."""

    scorer = AtsKeywordCoverageScorer(top_k=8)
    via_class = scorer.score("Rust SQL", "Rust SQL Go")
    via_fn = score_keyword_coverage("Rust SQL", "Rust SQL Go", top_k=8)
    assert via_class == via_fn


def test_invalid_top_k_raises() -> None:
    """top_k < 1 raises ValueError."""

    with pytest.raises(ValueError, match="top_k"):
        AtsKeywordCoverageScorer(top_k=0)


def test_deterministic() -> None:
    """Repeated scores are identical."""

    args = ("python redis postgres", "Python Redis Kafka Postgres")
    assert score_keyword_coverage(*args) == score_keyword_coverage(*args)

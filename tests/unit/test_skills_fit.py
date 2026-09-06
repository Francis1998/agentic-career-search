"""Unit tests for SkillsProfileFitScorer / score_skills_fit."""

from __future__ import annotations

from typing import TYPE_CHECKING

from autoapply_agent.services.skills_fit import SkillsProfileFitScorer, score_skills_fit

if TYPE_CHECKING:
    from _pytest.capture import CaptureFixture
    from _pytest.fixtures import FixtureRequest
    from _pytest.logging import LogCaptureFixture
    from _pytest.monkeypatch import MonkeyPatch
    from pytest_mock.plugin import MockerFixture


def test_empty_skills_yields_zero_fit() -> None:
    """Empty candidate skills list returns fit_score 0.0."""

    result = score_skills_fit([], "Python FastAPI engineer")
    assert result.fit_score == 0.0
    assert result.matched_skills == []
    assert result.missing_skills == []


def test_none_skills_yields_zero_fit() -> None:
    """None candidate skills behaves like empty."""

    result = score_skills_fit(None, "Python engineer")
    assert result.fit_score == 0.0
    assert result.matched_skills == []
    assert result.missing_skills == []


def test_partial_match() -> None:
    """Partial overlap produces fractional fit and split matched/missing."""

    result = score_skills_fit(
        ["Python", "Kubernetes", "Go"],
        "Looking for a Python engineer with Docker experience.",
    )
    assert result.matched_skills == ["Python"]
    assert result.missing_skills == ["Kubernetes", "Go"]
    assert result.fit_score == round(1 / 3, 4)


def test_full_match() -> None:
    """All skills present in job text yield fit_score 1.0."""

    result = score_skills_fit(
        ["Python", "FastAPI"],
        "Senior Python FastAPI engineer for APIs",
    )
    assert result.fit_score == 1.0
    assert result.matched_skills == ["Python", "FastAPI"]
    assert result.missing_skills == []


def test_case_insensitive_matching() -> None:
    """Matching is case-insensitive."""

    result = score_skills_fit(
        ["python", "FASTAPI"],
        "We need PYTHON and fastapi experience.",
    )
    assert result.fit_score == 1.0
    assert [s.lower() for s in result.matched_skills] == ["python", "fastapi"]
    assert result.missing_skills == []


def test_scorer_class_delegates() -> None:
    """SkillsProfileFitScorer.score mirrors the pure function."""

    scorer = SkillsProfileFitScorer()
    via_class = scorer.score(["SQL", "Rust"], "SQL analyst role")
    via_fn = score_skills_fit(["SQL", "Rust"], "SQL analyst role")
    assert via_class == via_fn
    assert via_class.fit_score == 0.5
    assert via_class.matched_skills == ["SQL"]
    assert via_class.missing_skills == ["Rust"]

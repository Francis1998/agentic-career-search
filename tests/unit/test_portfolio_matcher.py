"""Unit tests for PortfolioProjectMatcher."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from autoapply_agent.services.portfolio_matcher import (
    PortfolioMatchResult,
    PortfolioProjectMatcher,
)

if TYPE_CHECKING:
    from _pytest.capture import CaptureFixture
    from _pytest.fixtures import FixtureRequest
    from _pytest.logging import LogCaptureFixture
    from _pytest.monkeypatch import MonkeyPatch
    from pytest_mock.plugin import MockerFixture


def test_blank_bullets_raise() -> None:
    """Empty or whitespace-only portfolio bullets raise ValueError."""

    matcher = PortfolioProjectMatcher()
    with pytest.raises(ValueError, match="portfolio_bullets"):
        matcher.match(portfolio_bullets=[], jd_themes=["kubernetes"])
    with pytest.raises(ValueError, match="portfolio_bullets"):
        matcher.match(portfolio_bullets=["  ", ""], jd_themes=["kubernetes"])


def test_blank_themes_raise() -> None:
    """Empty or whitespace-only JD themes raise ValueError."""

    matcher = PortfolioProjectMatcher()
    with pytest.raises(ValueError, match="jd_themes"):
        matcher.match(portfolio_bullets=["Built a Python API"], jd_themes=[])
    with pytest.raises(ValueError, match="jd_themes"):
        matcher.match(portfolio_bullets=["Built a Python API"], jd_themes=[" "])


def test_token_overlap_match() -> None:
    """Bullets sharing theme tokens are matched with score in [0, 1]."""

    results = PortfolioProjectMatcher().match(
        portfolio_bullets=[
            "Built a FastAPI service on Kubernetes",
            "Designed a React dashboard for analytics",
            "Owned PostgreSQL schema migrations",
        ],
        jd_themes=["kubernetes orchestration", "react frontend", "golang microservices"],
    )
    assert len(results) == 3
    by_theme = {item.jd_theme: item for item in results}

    k8s = by_theme["kubernetes orchestration"]
    assert k8s.matched_bullets == ["Built a FastAPI service on Kubernetes"]
    assert 0.0 < k8s.score <= 1.0
    assert k8s.requires_human_review is True

    react = by_theme["react frontend"]
    assert react.matched_bullets == ["Designed a React dashboard for analytics"]
    assert react.score > 0.0

    go = by_theme["golang microservices"]
    assert go.matched_bullets == []
    assert go.score == 0.0
    assert go.requires_human_review is True


def test_full_theme_overlap_scores_one() -> None:
    """When a bullet covers every theme token, score is 1.0."""

    results = PortfolioProjectMatcher().match(
        portfolio_bullets=["Shipped python fastapi kubernetes platform"],
        jd_themes=["Python FastAPI"],
    )
    assert len(results) == 1
    assert results[0].score == 1.0
    assert results[0].matched_bullets == [
        "Shipped python fastapi kubernetes platform",
    ]


def test_case_insensitive() -> None:
    """Matching is case-insensitive."""

    results = PortfolioProjectMatcher().match(
        portfolio_bullets=["Built PYTHON microservices"],
        jd_themes=["Python"],
    )
    assert results[0].score == 1.0
    assert results[0].matched_bullets


def test_requires_human_review_always() -> None:
    """Every result flags HITL review."""

    results = PortfolioProjectMatcher().match(
        portfolio_bullets=["Owned CI pipelines"],
        jd_themes=["ci", "rust"],
    )
    assert all(isinstance(item, PortfolioMatchResult) for item in results)
    assert all(item.requires_human_review is True for item in results)


def test_no_network_calls() -> None:
    """Matcher never performs HTTP calls."""

    with (
        patch("httpx.Client", MagicMock()) as client_cls,
        patch("httpx.AsyncClient", MagicMock()) as async_cls,
        patch("httpx.get", MagicMock()) as get_fn,
        patch("httpx.post", MagicMock()) as post_fn,
    ):
        PortfolioProjectMatcher().match(
            portfolio_bullets=["Built a Redis cache layer"],
            jd_themes=["redis caching"],
        )
        client_cls.assert_not_called()
        async_cls.assert_not_called()
        get_fn.assert_not_called()
        post_fn.assert_not_called()


def test_deterministic() -> None:
    """Repeated match calls are identical."""

    matcher = PortfolioProjectMatcher()
    kwargs = {
        "portfolio_bullets": [
            "Built a FastAPI service on Kubernetes",
            "Designed a React dashboard",
        ],
        "jd_themes": ["kubernetes", "react", "golang"],
    }
    assert matcher.match(**kwargs) == matcher.match(**kwargs)

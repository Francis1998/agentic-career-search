"""Unit tests for LinkedInHeadlineKeywordScorer."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from autoapply_agent.services.linkedin_headline import LinkedInHeadlineKeywordScorer


def test_blank_headline_raises() -> None:
    """Blank headline raises ValueError."""

    with pytest.raises(ValueError, match="headline"):
        LinkedInHeadlineKeywordScorer().score("  ", ["python", "fastapi"])


def test_empty_keywords_raises() -> None:
    """Empty target_keywords raises ValueError."""

    with pytest.raises(ValueError, match="target_keywords"):
        LinkedInHeadlineKeywordScorer().score("Python Engineer", [])


def test_coverage_present_and_missing() -> None:
    """Scores present vs missing keywords."""

    report = LinkedInHeadlineKeywordScorer().score(
        "Senior Python Engineer | FastAPI | Distributed Systems",
        ["python", "fastapi", "kubernetes", "distributed systems"],
    )
    assert "python" in report.present_keywords
    assert "fastapi" in report.present_keywords
    assert "distributed systems" in report.present_keywords
    assert "kubernetes" in report.missing_keywords
    assert report.requires_human_review is True
    assert report.auto_post is False


def test_no_network_calls() -> None:
    """Scorer never performs HTTP calls."""

    with (
        patch("httpx.Client", MagicMock()) as client_cls,
        patch("httpx.AsyncClient", MagicMock()) as async_cls,
        patch("httpx.get", MagicMock()) as get_fn,
        patch("httpx.post", MagicMock()) as post_fn,
    ):
        LinkedInHeadlineKeywordScorer().score("ML Engineer", ["ml", "pytorch"])
        client_cls.assert_not_called()
        async_cls.assert_not_called()
        get_fn.assert_not_called()
        post_fn.assert_not_called()

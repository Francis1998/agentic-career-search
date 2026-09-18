"""Unit tests for ApplicationPacketCompletenessGate."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from autoapply_agent.services.packet_completeness import ApplicationPacketCompletenessGate


def test_missing_resume_and_cover() -> None:
    """Blank resume/cover letter yields missing required artifacts."""

    report = ApplicationPacketCompletenessGate().evaluate()
    assert report.auto_submit is False
    assert report.requires_human_review is True
    assert "resume" in report.missing_required
    assert "cover_letter" in report.missing_required
    assert report.ready_for_human_submit is False
    assert report.completeness_score == 0.0


def test_ready_when_required_present() -> None:
    """Resume + cover letter unlock ready_for_human_submit."""

    report = ApplicationPacketCompletenessGate().evaluate(
        resume_text="Backend engineer resume",
        cover_letter_text="Excited about the role",
    )
    assert report.missing_required == []
    assert report.ready_for_human_submit is True
    assert report.completeness_score == 1.0
    assert report.auto_submit is False


def test_optional_portfolio_required_flag() -> None:
    """require_portfolio adds portfolio to missing_required when blank."""

    report = ApplicationPacketCompletenessGate().evaluate(
        resume_text="Resume",
        cover_letter_text="Cover",
        require_portfolio=True,
    )
    assert "portfolio" in report.missing_required
    assert report.ready_for_human_submit is False


def test_no_network_calls() -> None:
    """Gate never performs HTTP calls."""

    with (
        patch("httpx.Client", MagicMock()) as client_cls,
        patch("httpx.AsyncClient", MagicMock()) as async_cls,
        patch("httpx.get", MagicMock()) as get_fn,
        patch("httpx.post", MagicMock()) as post_fn,
    ):
        ApplicationPacketCompletenessGate().evaluate(resume_text="x", cover_letter_text="y")
        client_cls.assert_not_called()
        async_cls.assert_not_called()
        get_fn.assert_not_called()
        post_fn.assert_not_called()

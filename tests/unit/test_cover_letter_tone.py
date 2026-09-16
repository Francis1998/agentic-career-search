"""Unit tests for CoverLetterToneAligner."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from autoapply_agent.services.cover_letter_tone import CoverLetterToneAligner


def test_blank_cover_letter_raises() -> None:
    """Blank cover_letter raises ValueError."""

    with pytest.raises(ValueError, match="cover_letter"):
        CoverLetterToneAligner().align("  ", "fast-paced startup role")


def test_blank_jd_raises() -> None:
    """Blank job_description raises ValueError."""

    with pytest.raises(ValueError, match="job_description"):
        CoverLetterToneAligner().align("Excited to contribute.", "  ")


def test_energetic_alignment() -> None:
    """Energetic letter cues align to fast-paced JD."""

    report = CoverLetterToneAligner().align(
        "I am excited and passionate about shipping with your team.",
        "We are a fast-paced startup that likes to move fast.",
    )
    bands = {m.band for m in report.matches}
    assert "energetic" in bands
    assert report.requires_human_review is True
    assert report.auto_send is False


def test_missing_jd_band_flagged() -> None:
    """JD technical cues without letter hits appear in missing_jd_bands."""

    report = CoverLetterToneAligner().align(
        "Dear Hiring Manager, I am pleased to submit my application. Sincerely,",
        "We need distributed systems scalability and infrastructure reliability.",
    )
    assert "technical" in report.missing_jd_bands


def test_no_network_calls() -> None:
    """Aligner never performs HTTP calls."""

    with (
        patch("httpx.Client", MagicMock()) as client_cls,
        patch("httpx.AsyncClient", MagicMock()) as async_cls,
        patch("httpx.get", MagicMock()) as get_fn,
        patch("httpx.post", MagicMock()) as post_fn,
    ):
        CoverLetterToneAligner().align(
            "Excited to collaborate cross-functional.",
            "Collaborate with a cross-functional squad.",
        )
        client_cls.assert_not_called()
        async_cls.assert_not_called()
        get_fn.assert_not_called()
        post_fn.assert_not_called()

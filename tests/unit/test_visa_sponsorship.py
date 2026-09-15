"""Unit tests for VisaSponsorshipSignalExtractor."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from autoapply_agent.services.visa_sponsorship import VisaSponsorshipSignalExtractor

if TYPE_CHECKING:
    from _pytest.capture import CaptureFixture
    from _pytest.fixtures import FixtureRequest
    from _pytest.logging import LogCaptureFixture
    from _pytest.monkeypatch import MonkeyPatch
    from pytest_mock.plugin import MockerFixture


def test_blank_company_raises() -> None:
    """Blank company raises ValueError."""

    with pytest.raises(ValueError, match="company"):
        VisaSponsorshipSignalExtractor().extract(
            company=" ",
            role="Backend Engineer",
            jd_text="Visa sponsorship available for H-1B.",
        )


def test_blank_jd_raises() -> None:
    """Blank jd_text raises ValueError."""

    with pytest.raises(ValueError, match="jd_text"):
        VisaSponsorshipSignalExtractor().extract(
            company="Acme",
            role="Backend Engineer",
            jd_text="",
        )


def test_extracts_sponsorship_and_no_sponsor_cues() -> None:
    """Known visa phrases become typed signals with evidence."""

    report = VisaSponsorshipSignalExtractor().extract(
        company="Acme",
        role="Backend Engineer",
        jd_text=(
            "We offer visa sponsorship for qualified H-1B candidates. "
            "Visa transfer and cap-exempt roles are also considered."
        ),
    )
    names = {item.signal for item in report.signals}
    assert "sponsors_visa" in names
    assert "visa_transfer_ok" in names
    assert all(item.evidence for item in report.signals)


def test_citizenship_and_no_sponsorship() -> None:
    """Citizenship-only and no-sponsorship cues are detected."""

    report = VisaSponsorshipSignalExtractor().extract(
        company="GovCorp",
        role="Analyst",
        jd_text="US citizens only. We are unable to sponsor visas. Clearance required.",
    )
    names = {item.signal for item in report.signals}
    assert "citizenship_required" in names
    assert "no_sponsorship" in names


def test_conflicting_cues_add_guidance() -> None:
    """Conflicting sponsor vs no-sponsor cues add HITL guidance."""

    report = VisaSponsorshipSignalExtractor().extract(
        company="Acme",
        role="SRE",
        jd_text="Visa sponsorship available. We cannot sponsor new grads.",
    )
    assert any("Conflicting" in line for line in report.guidance)


def test_no_signals_still_emits_guidance() -> None:
    """Unmatched JD text still yields HITL guidance."""

    report = VisaSponsorshipSignalExtractor().extract(
        company="Acme",
        role="Analyst",
        jd_text="Write reports and maintain spreadsheets.",
    )
    assert report.signals == []
    assert report.guidance


def test_never_auto_applies_requires_human_review() -> None:
    """Every payload flags HITL review and never auto-applies."""

    report = VisaSponsorshipSignalExtractor().extract(
        company="Acme",
        role="SRE",
        jd_text="H-1B visa sponsorship available.",
    )
    assert report.requires_human_review is True
    assert report.auto_apply is False


def test_no_network_calls() -> None:
    """Extractor never performs HTTP calls."""

    with (
        patch("httpx.Client", MagicMock()) as client_cls,
        patch("httpx.AsyncClient", MagicMock()) as async_cls,
        patch("httpx.get", MagicMock()) as get_fn,
        patch("httpx.post", MagicMock()) as post_fn,
    ):
        VisaSponsorshipSignalExtractor().extract(
            company="Acme",
            role="PM",
            jd_text="Must already be authorized to work without sponsorship.",
        )
        client_cls.assert_not_called()
        async_cls.assert_not_called()
        get_fn.assert_not_called()
        post_fn.assert_not_called()

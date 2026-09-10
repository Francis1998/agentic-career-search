"""Unit tests for NegotiationTalkingPointsService."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from autoapply_agent.services.negotiation_talking import NegotiationTalkingPointsService

if TYPE_CHECKING:
    from _pytest.capture import CaptureFixture
    from _pytest.fixtures import FixtureRequest
    from _pytest.logging import LogCaptureFixture
    from _pytest.monkeypatch import MonkeyPatch
    from pytest_mock.plugin import MockerFixture


def test_empty_company_raises() -> None:
    """Blank company name raises ValueError."""

    with pytest.raises(ValueError, match="company"):
        NegotiationTalkingPointsService().generate(
            company=" ",
            role="SWE",
            current_total_usd=180_000,
            target_total_usd=200_000,
        )


def test_non_positive_current_raises() -> None:
    """Non-positive current_total_usd raises ValueError."""

    with pytest.raises(ValueError, match="current_total_usd"):
        NegotiationTalkingPointsService().generate(
            company="Acme",
            role="SWE",
            current_total_usd=0,
            target_total_usd=200_000,
        )


def test_target_not_greater_raises() -> None:
    """target_total_usd <= current_total_usd raises ValueError."""

    with pytest.raises(ValueError, match="target_total_usd"):
        NegotiationTalkingPointsService().generate(
            company="Acme",
            role="SWE",
            current_total_usd=200_000,
            target_total_usd=200_000,
        )


def test_points_always_require_human_review() -> None:
    """Every payload flags requires_human_review=True and never auto-sends."""

    points = NegotiationTalkingPointsService().generate(
        company="Acme",
        role="Platform Engineer",
        current_total_usd=190_000,
        target_total_usd=215_000,
        leverage_notes="Competing offer from Nimbus",
    )
    assert points.requires_human_review is True
    assert points.company == "Acme"
    assert points.current_total_usd == 190_000
    assert points.target_total_usd == 215_000
    assert any("do not auto-send" in item.lower() for item in points.talking_points)
    assert any("Competing offer" in item for item in points.talking_points)
    assert points.risks


def test_no_network_calls() -> None:
    """Generator never performs HTTP calls."""

    with (
        patch("httpx.Client", MagicMock()) as client_cls,
        patch("httpx.AsyncClient", MagicMock()) as async_cls,
        patch("httpx.get", MagicMock()) as get_fn,
        patch("httpx.post", MagicMock()) as post_fn,
    ):
        NegotiationTalkingPointsService().generate(
            company="Globex",
            role="SRE",
            current_total_usd=170_000,
            target_total_usd=185_000,
        )
        client_cls.assert_not_called()
        async_cls.assert_not_called()
        get_fn.assert_not_called()
        post_fn.assert_not_called()


def test_deterministic() -> None:
    """Repeated generate calls are identical."""

    service = NegotiationTalkingPointsService()
    kwargs = {
        "company": "Acme",
        "role": "SWE",
        "current_total_usd": 180_000,
        "target_total_usd": 200_000,
        "leverage_notes": "Strong on-call ownership",
    }
    assert service.generate(**kwargs) == service.generate(**kwargs)

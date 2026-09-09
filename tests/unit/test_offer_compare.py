"""Unit tests for OfferCompareMatrix."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from autoapply_agent.services.offer_compare import OfferCompareMatrix

if TYPE_CHECKING:
    from _pytest.capture import CaptureFixture
    from _pytest.fixtures import FixtureRequest
    from _pytest.logging import LogCaptureFixture
    from _pytest.monkeypatch import MonkeyPatch
    from pytest_mock.plugin import MockerFixture


def test_empty_list_raises() -> None:
    """Empty offers list raises ValueError."""

    with pytest.raises(ValueError, match="offers"):
        OfferCompareMatrix().compare([])


def test_ranking_by_total_cash_plus_equity() -> None:
    """Offers rank by base+bonus+equity heuristic (highest first)."""

    result = OfferCompareMatrix().compare(
        [
            {
                "company": "Acme",
                "base": 150_000,
                "bonus": 10_000,
                "equity": 20_000,
                "remote": "hybrid",
                "notes": "good team",
            },
            {
                "company": "Globex",
                "base": 140_000,
                "bonus": 5_000,
                "equity": 80_000,
                "remote": "remote",
                "notes": "",
            },
            {
                "company": "Initech",
                "base": 160_000,
                "bonus": 0,
                "equity": 5_000,
                "remote": "onsite",
                "notes": "commute",
            },
        ]
    )

    assert result.auto_accept is False
    assert [row.company for row in result.rows] == ["Globex", "Acme", "Initech"]
    assert result.rows[0].rank == 1
    assert result.rows[0].total_comp == 225_000
    assert result.rows[1].total_comp == 180_000
    assert result.rows[2].total_comp == 165_000
    assert "Globex" in result.summary
    assert "never auto-accept" in result.summary.lower()


def test_deterministic() -> None:
    """Repeated compare calls are identical."""

    offers = [
        {"company": "A", "base": 100, "bonus": 10, "equity": 5, "remote": "remote"},
        {"company": "B", "base": 120, "bonus": 0, "equity": 0, "remote": "onsite"},
    ]
    assert OfferCompareMatrix().compare(offers) == OfferCompareMatrix().compare(offers)


def test_no_network_calls() -> None:
    """Comparator never performs HTTP calls."""

    with (
        patch("httpx.Client", MagicMock()) as client_cls,
        patch("httpx.AsyncClient", MagicMock()) as async_cls,
        patch("httpx.get", MagicMock()) as get_fn,
        patch("httpx.post", MagicMock()) as post_fn,
    ):
        OfferCompareMatrix().compare(
            [{"company": "Acme", "base": 1, "bonus": 0, "equity": 0, "remote": "remote"}]
        )
        client_cls.assert_not_called()
        async_cls.assert_not_called()
        get_fn.assert_not_called()
        post_fn.assert_not_called()


def test_blank_company_raises() -> None:
    """Blank company on an offer raises ValueError."""

    with pytest.raises(ValueError, match="company"):
        OfferCompareMatrix().compare([{"company": "  ", "base": 100, "bonus": 0, "equity": 0}])

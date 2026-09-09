"""Unit tests for LocationRemoteFitScorer."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

from autoapply_agent.services.location_remote_fit import LocationRemoteFitScorer

if TYPE_CHECKING:
    from _pytest.capture import CaptureFixture
    from _pytest.fixtures import FixtureRequest
    from _pytest.logging import LogCaptureFixture
    from _pytest.monkeypatch import MonkeyPatch
    from pytest_mock.plugin import MockerFixture


def test_remote_match_scores_high() -> None:
    """Preferring remote against a remote-friendly posting scores highly."""

    result = LocationRemoteFitScorer().score(
        candidate_locations=["Austin, TX"],
        prefers_remote=True,
        posting_location="Remote - US",
        posting_remote_policy="Fully remote",
    )
    assert 0.0 <= result.fit_score <= 1.0
    assert result.fit_score >= 0.6
    assert any("remote" in reason.lower() for reason in result.reasons)


def test_geo_mismatch_lowers_score() -> None:
    """Onsite posting in a different city yields geo-mismatch reason."""

    result = LocationRemoteFitScorer().score(
        candidate_locations=["Seattle, WA"],
        prefers_remote=False,
        posting_location="New York, NY",
        posting_remote_policy="Onsite only",
    )
    assert 0.0 <= result.fit_score <= 1.0
    assert result.fit_score < 0.6
    assert any("geo mismatch" in reason.lower() for reason in result.reasons)


def test_blank_inputs_score_zero() -> None:
    """All-blank inputs return fit_score 0.0 with an explanatory reason."""

    result = LocationRemoteFitScorer().score(
        candidate_locations=[],
        prefers_remote=False,
        posting_location="",
        posting_remote_policy=None,
    )
    assert result.fit_score == 0.0
    assert any("blank" in reason.lower() for reason in result.reasons)


def test_geo_overlap_boosts_score() -> None:
    """Matching city tokens boost the fit score."""

    result = LocationRemoteFitScorer().score(
        candidate_locations=["San Francisco, CA"],
        prefers_remote=False,
        posting_location="San Francisco Bay Area",
        posting_remote_policy="Hybrid",
    )
    assert result.fit_score >= 0.5
    assert any("overlap" in reason.lower() for reason in result.reasons)


def test_deterministic() -> None:
    """Repeated score calls are identical."""

    kwargs = {
        "candidate_locations": ["Berlin"],
        "prefers_remote": True,
        "posting_location": "Berlin, Germany",
        "posting_remote_policy": "hybrid remote",
    }
    assert LocationRemoteFitScorer().score(**kwargs) == LocationRemoteFitScorer().score(**kwargs)


def test_no_network_calls() -> None:
    """Scorer never performs HTTP calls."""

    with (
        patch("httpx.Client", MagicMock()) as client_cls,
        patch("httpx.AsyncClient", MagicMock()) as async_cls,
        patch("httpx.get", MagicMock()) as get_fn,
        patch("httpx.post", MagicMock()) as post_fn,
    ):
        LocationRemoteFitScorer().score(
            candidate_locations=["Remote"],
            prefers_remote=True,
            posting_location="Anywhere",
            posting_remote_policy="remote",
        )
        client_cls.assert_not_called()
        async_cls.assert_not_called()
        get_fn.assert_not_called()
        post_fn.assert_not_called()

"""Unit tests for RemoteTimezoneOverlapAdvisor."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from autoapply_agent.services.timezone_overlap import RemoteTimezoneOverlapAdvisor


def test_same_zone_full_core_is_strong() -> None:
    """Matching offsets with 8h candidate day covering 9-17 yields strong."""

    report = RemoteTimezoneOverlapAdvisor().advise(
        candidate_utc_offset_hours=-8.0,
        team_utc_offset_hours=-8.0,
        team_core_start_local=9.0,
        team_core_end_local=17.0,
        candidate_day_start=8.0,
        candidate_day_end=20.0,
    )
    assert report.overlap_hours == 8.0
    assert report.overlap_band == "strong"
    assert report.auto_apply is False
    assert report.requires_human_review is True


def test_opposite_zone_is_none_or_thin() -> None:
    """Large offset gap yields none/thin overlap."""

    report = RemoteTimezoneOverlapAdvisor().advise(
        candidate_utc_offset_hours=9.0,
        team_utc_offset_hours=-8.0,
        team_core_start_local=9.0,
        team_core_end_local=17.0,
        candidate_day_start=9.0,
        candidate_day_end=17.0,
    )
    assert report.overlap_band in {"none", "thin"}
    assert report.overlap_hours < 3.0


def test_invalid_core_window_raises() -> None:
    """Inverted team core window raises ValueError."""

    with pytest.raises(ValueError, match="team_core_end_local"):
        RemoteTimezoneOverlapAdvisor().advise(
            candidate_utc_offset_hours=0.0,
            team_core_start_local=17.0,
            team_core_end_local=9.0,
        )


def test_offset_out_of_range_raises() -> None:
    """Offsets outside [-14, 14] raise ValueError."""

    with pytest.raises(ValueError, match="candidate_utc_offset_hours"):
        RemoteTimezoneOverlapAdvisor().advise(candidate_utc_offset_hours=20.0)


def test_no_network_calls() -> None:
    """Advisor never performs HTTP calls."""

    with (
        patch("httpx.Client", MagicMock()) as client_cls,
        patch("httpx.AsyncClient", MagicMock()) as async_cls,
        patch("httpx.get", MagicMock()) as get_fn,
        patch("httpx.post", MagicMock()) as post_fn,
    ):
        RemoteTimezoneOverlapAdvisor().advise(candidate_utc_offset_hours=-5.0)
        client_cls.assert_not_called()
        async_cls.assert_not_called()
        get_fn.assert_not_called()
        post_fn.assert_not_called()

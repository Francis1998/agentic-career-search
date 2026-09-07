"""Unit tests for SalaryBandEstimator (assistive, non-authoritative)."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import httpx

from autoapply_agent.services.salary_band import SalaryBandEstimator, parse_level_from_title

if TYPE_CHECKING:
    from _pytest.capture import CaptureFixture
    from _pytest.fixtures import FixtureRequest
    from _pytest.logging import LogCaptureFixture
    from _pytest.monkeypatch import MonkeyPatch
    from pytest_mock.plugin import MockerFixture


def test_parse_level_from_title_senior() -> None:
    """Senior titles map to the senior level bucket."""

    assert parse_level_from_title("Senior Backend Engineer") == "senior"
    assert parse_level_from_title("Staff Platform Engineer") == "staff"
    assert parse_level_from_title("Software Engineer") == "unknown"


def test_estimate_senior_sf_raises_band() -> None:
    """SF location increases the mid band above baseline senior mid."""

    estimate = SalaryBandEstimator().estimate(
        job_title="Senior Backend Engineer",
        location="San Francisco, CA",
    )
    assert estimate.currency == "USD"
    assert estimate.level == "senior"
    assert estimate.location_factor == 1.25
    assert estimate.low < estimate.mid < estimate.high
    assert estimate.mid >= 200_000
    assert 0.0 <= estimate.confidence <= 1.0
    assert estimate.rationale


def test_estimate_remote_token_from_job_text() -> None:
    """Remote tokens in job text apply a modest uplift."""

    estimate = SalaryBandEstimator().estimate(
        job_title="Platform Engineer",
        job_text="Fully remote role, work from anywhere.",
    )
    assert estimate.location_factor == 1.05
    assert estimate.level == "unknown"


def test_estimate_never_performs_http() -> None:
    """Salary estimation must not open network connections."""

    with (
        patch.object(httpx, "Client", side_effect=AssertionError("no httpx.Client")),
        patch.object(httpx, "AsyncClient", side_effect=AssertionError("no AsyncClient")),
        patch("httpx.post", MagicMock(side_effect=AssertionError("no httpx.post"))),
        patch("httpx.get", MagicMock(side_effect=AssertionError("no httpx.get"))),
    ):
        estimate = SalaryBandEstimator().estimate(job_title="Junior Data Engineer")

    assert estimate.level == "junior"
    assert estimate.currency == "USD"


def test_estimate_is_deterministic() -> None:
    """Same inputs produce identical estimates."""

    kwargs = {
        "job_title": "Staff SRE",
        "location": "Seattle",
        "job_text": "Kubernetes ownership.",
    }
    assert SalaryBandEstimator().estimate(**kwargs) == SalaryBandEstimator().estimate(**kwargs)

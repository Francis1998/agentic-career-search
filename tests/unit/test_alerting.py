"""Unit tests for priority alert webhook helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from autoapply_agent.core.config import Settings
from autoapply_agent.services.alerting import (
    build_priority_alert_payload,
    send_priority_alert,
    send_priority_alert_async,
    should_send_priority_alert,
)

if TYPE_CHECKING:
    from _pytest.capture import CaptureFixture
    from _pytest.fixtures import FixtureRequest
    from _pytest.logging import LogCaptureFixture
    from _pytest.monkeypatch import MonkeyPatch
    from pytest_mock.plugin import MockerFixture


def _enabled_settings(url: str = "https://hooks.example.com/alert") -> Settings:
    """Build settings with alerting enabled."""

    return Settings(
        PRIORITY_ALERT_WEBHOOK_ENABLED=True,
        PRIORITY_ALERT_WEBHOOK_URL=url,
        PRIORITY_ALERT_WEBHOOK_TIMEOUT_SECONDS=2.0,
    )


def test_should_send_only_for_high_when_enabled() -> None:
    """Only high-tier decisions trigger alerts when the feature flag is on."""

    config = _enabled_settings()
    assert should_send_priority_alert("high", config=config) is True
    assert should_send_priority_alert("medium", config=config) is False
    assert should_send_priority_alert("low", config=config) is False


def test_should_not_send_when_disabled_or_missing_url() -> None:
    """Disabled flag or empty URL must skip the webhook."""

    disabled = Settings(
        PRIORITY_ALERT_WEBHOOK_ENABLED=False,
        PRIORITY_ALERT_WEBHOOK_URL="https://hooks.example.com/alert",
    )
    missing_url = Settings(
        PRIORITY_ALERT_WEBHOOK_ENABLED=True,
        PRIORITY_ALERT_WEBHOOK_URL=None,
    )
    assert should_send_priority_alert("high", config=disabled) is False
    assert should_send_priority_alert("high", config=missing_url) is False


def test_build_priority_alert_payload_shape() -> None:
    """Payload includes event type and core correlation fields."""

    payload = build_priority_alert_payload(
        run_id="run-1",
        job_title="Staff Backend Engineer",
        job_url="https://example.com/jobs/1",
        company="Example",
        score=0.91,
        priority_tier="high",
        extra={"matched_terms": ["backend"]},
    )
    assert payload["event"] == "priority.alert"
    assert payload["priority_tier"] == "high"
    assert payload["run_id"] == "run-1"
    assert payload["matched_terms"] == ["backend"]


def test_send_priority_alert_posts_json() -> None:
    """Sync helper POSTs JSON and returns True on success."""

    config = _enabled_settings()
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.post.return_value = mock_response

    delivered = send_priority_alert(
        "high",
        run_id="run-42",
        job_title="Platform Engineer",
        job_url="https://example.com/jobs/42",
        company="Acme",
        score=0.88,
        config=config,
        client=mock_client,
    )

    assert delivered is True
    mock_client.post.assert_called_once()
    args, kwargs = mock_client.post.call_args
    assert args[0] == "https://hooks.example.com/alert"
    assert kwargs["json"]["priority_tier"] == "high"
    assert kwargs["json"]["job_title"] == "Platform Engineer"


def test_send_priority_alert_skips_non_high() -> None:
    """Medium/low tiers never call the HTTP client."""

    config = _enabled_settings()
    mock_client = MagicMock(spec=httpx.Client)
    delivered = send_priority_alert(
        "medium",
        job_title="Intern",
        config=config,
        client=mock_client,
    )
    assert delivered is False
    mock_client.post.assert_not_called()


def test_send_priority_alert_fail_soft_on_http_error() -> None:
    """HTTP failures are logged and return False without raising."""

    config = _enabled_settings()
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.post.side_effect = httpx.ConnectError("boom")

    delivered = send_priority_alert(
        "high",
        job_title="SRE",
        config=config,
        client=mock_client,
    )
    assert delivered is False


@pytest.mark.asyncio
async def test_send_priority_alert_async_posts_json() -> None:
    """Async helper POSTs JSON and returns True on success."""

    config = _enabled_settings()
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post.return_value = mock_response

    delivered = await send_priority_alert_async(
        "high",
        run_id="run-async",
        job_title="ML Engineer",
        config=config,
        client=mock_client,
    )
    assert delivered is True
    mock_client.post.assert_awaited_once()


@pytest.mark.asyncio
async def test_send_priority_alert_async_fail_soft() -> None:
    """Async helper swallows transport errors (fail-soft)."""

    config = _enabled_settings()
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post.side_effect = httpx.TimeoutException("timeout")

    delivered = await send_priority_alert_async(
        "high",
        job_title="Data Engineer",
        config=config,
        client=mock_client,
    )
    assert delivered is False

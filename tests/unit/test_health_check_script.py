"""Unit tests for the local health-check script."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from _pytest.capture import CaptureFixture
    from _pytest.fixtures import FixtureRequest
    from _pytest.logging import LogCaptureFixture
    from _pytest.monkeypatch import MonkeyPatch
    from pytest_mock.plugin import MockerFixture


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "health_check.py"


class FakeHealthResponse:
    """Context manager that mimics urllib response objects."""

    def __init__(self, payload: dict[str, str], status: int = 200) -> None:
        """Initialize the fake response payload and HTTP status."""

        self.payload = payload
        self.status = status

    def __enter__(self) -> FakeHealthResponse:
        """Return the active fake response."""

        return self

    def __exit__(self, *_exc_info: object) -> None:
        """Exit the fake response context."""

    def read(self) -> bytes:
        """Return the encoded JSON payload."""

        return json.dumps(self.payload).encode("utf-8")


def load_health_check_module() -> ModuleType:
    """Load the health-check script as a Python module."""

    spec = importlib.util.spec_from_file_location("health_check_script", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_check_health_probes_liveness_and_readiness(monkeypatch: MonkeyPatch) -> None:
    """Health check should use the API's live and ready endpoints."""

    module = load_health_check_module()
    requested_urls: list[str] = []

    def fake_urlopen(url: str, timeout: float) -> FakeHealthResponse:
        """Capture health-check URLs and return healthy payloads."""

        assert timeout == 5.0
        requested_urls.append(url)
        return FakeHealthResponse({"status": "ok"})

    monkeypatch.setattr(module.request, "urlopen", fake_urlopen)

    assert module.check_health(base_url="http://service.local") is True
    assert requested_urls == [
        "http://service.local/health/live",
        "http://service.local/health/ready",
    ]


def test_check_health_fails_on_unhealthy_endpoint(monkeypatch: MonkeyPatch) -> None:
    """Health check should fail when any probe returns a non-200 status."""

    module = load_health_check_module()

    def fake_urlopen(url: str, timeout: float) -> FakeHealthResponse:
        """Return an unhealthy readiness response after liveness succeeds."""

        payload: dict[str, str] = {"status": "ready"}
        status = 503 if url.endswith("/health/ready") else 200
        return FakeHealthResponse(payload, status=status)

    monkeypatch.setattr(module.request, "urlopen", fake_urlopen)

    assert module.check_health(base_url="http://service.local") is False

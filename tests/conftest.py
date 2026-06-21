"""Shared pytest fixtures for application tests."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from autoapply_agent.core.config import Settings

if TYPE_CHECKING:
    from _pytest.capture import CaptureFixture
    from _pytest.fixtures import FixtureRequest
    from _pytest.logging import LogCaptureFixture
    from _pytest.monkeypatch import MonkeyPatch
    from pytest_mock.plugin import MockerFixture


@pytest.fixture()
def sqlite_database_url(tmp_path: Path) -> str:
    """Create isolated sqlite URL for a test.

    Args:
        tmp_path: Pytest temp path fixture.

    Returns:
        Async sqlite database URL.
    """

    db_path = tmp_path / "test.db"
    return f"sqlite+aiosqlite:///{db_path}"


@pytest.fixture()
def test_settings(sqlite_database_url: str) -> Settings:
    """Build default test settings with worker enabled.

    Args:
        sqlite_database_url: Test database URL.

    Returns:
        Settings instance for test app creation.
    """

    return Settings(
        APP_NAME="autoapply-test",
        DATABASE_URL=sqlite_database_url,
        WORKER_POLL_INTERVAL_SECONDS=0.05,
        HTTP_TIMEOUT_SECONDS=1.0,
        MAX_JOBS_PER_SOURCE=10,
        HTTP_USER_AGENT="autoapply-test-agent",
        ENABLE_WORKER=True,
        ENVIRONMENT="test",
    )

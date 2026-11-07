"""Integer inputs outside SQLite's INTEGER range must be rejected, not crash queries."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from autoapply_agent.core.config import Settings
from autoapply_agent.main import create_app

# SQLite INTEGER columns and rowids are signed 64-bit; binding anything larger raises
# OverflowError inside the query.
SQLITE_MAX = 2**63 - 1
TOO_BIG = SQLITE_MAX + 1
TOO_SMALL = -(2**63) - 1


@pytest.fixture()
def client(sqlite_database_url: str) -> Iterator[TestClient]:
    """Start the API without the worker.

    Args:
        sqlite_database_url: Isolated test database URL.

    Yields:
        Test client bound to a fresh app.
    """

    settings = Settings(
        APP_NAME="integer-bounds-test",
        DATABASE_URL=sqlite_database_url,
        ENABLE_WORKER=False,
        ENVIRONMENT="test",
    )
    with TestClient(create_app(settings)) as test_client:
        yield test_client


@pytest.mark.parametrize(
    ("method", "path", "param"),
    [
        ("GET", f"/jobs?offset={TOO_BIG}", "offset"),
        ("GET", f"/jobs?source_config_id={TOO_BIG}", "source_config_id"),
        ("GET", f"/jobs/export?source_config_id={TOO_BIG}", "source_config_id"),
        ("GET", f"/jobs/feed.atom?source_config_id={TOO_BIG}", "source_config_id"),
        ("GET", f"/jobs/{TOO_BIG}", "job_id"),
        ("GET", f"/jobs/{TOO_SMALL}", "job_id"),
        ("GET", f"/source-configs/{TOO_BIG}", "source_config_id"),
        ("GET", f"/source-configs/{TOO_SMALL}", "source_config_id"),
        ("PATCH", f"/source-configs/{TOO_BIG}", "source_config_id"),
    ],
)
def test_out_of_range_integer_parameters_return_422(
    client: TestClient, method: str, path: str, param: str
) -> None:
    """Oversized ids and offsets fail validation instead of overflowing the query.

    Args:
        client: API test client.
        method: HTTP method.
        path: Request path with the out-of-range value.
        param: Parameter expected in the validation error location.
    """

    response = client.request(method, path, json={"enabled": False} if method == "PATCH" else None)

    assert response.status_code == 422, response.text
    assert [error["loc"][-1] for error in response.json()["detail"]] == [param]


def test_run_with_out_of_range_source_config_id_is_rejected(client: TestClient) -> None:
    """A run that could only fail in the worker is refused when it is queued.

    Args:
        client: API test client.
    """

    response = client.post("/runs", json={"source_config_ids": [1, TOO_BIG]})

    assert response.status_code == 422, response.text
    assert [error["loc"] for error in response.json()["detail"]] == [
        ["body", "source_config_ids", 1]
    ]


def test_largest_sqlite_integers_are_still_accepted(client: TestClient) -> None:
    """The bounds sit exactly at SQLite's limit: in-range values keep their behaviour.

    Args:
        client: API test client.
    """

    page = client.get(f"/jobs?offset={SQLITE_MAX}&source_config_id={SQLITE_MAX}")
    assert page.status_code == 200
    assert page.json() == []
    assert page.headers["X-Total-Count"] == "0"

    assert client.get(f"/jobs/{SQLITE_MAX}").json() == {"detail": "job not found"}
    assert client.get(f"/source-configs/{SQLITE_MAX}").status_code == 404

    run = client.post("/runs", json={"source_config_ids": [SQLITE_MAX]})
    assert run.status_code == 201
    assert run.json()["source_config_ids"] == [SQLITE_MAX]

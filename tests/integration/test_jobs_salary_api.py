"""Pay filters and sorting on GET /jobs, export, Atom feed, POST /jobs/match and MCP."""

from __future__ import annotations

import asyncio
import csv
import io
import json
import xml.etree.ElementTree as ET
from collections.abc import Iterator
from datetime import timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient

from autoapply_agent.core.config import Settings
from autoapply_agent.core.time import utc_now
from autoapply_agent.db.base import Base
from autoapply_agent.db.models import SQLITE_MAX_INTEGER, Job, Run, RunStatus, SourceConfig
from autoapply_agent.db.session import create_engine, create_session_factory
from autoapply_agent.main import create_app
from autoapply_agent.mcp.database import open_read_only_database
from autoapply_agent.mcp.server import CareerSearchMcpServer
from autoapply_agent.services import job_search
from autoapply_agent.services.compensation import (
    CompensationSource,
    PayInterval,
    compensation_columns,
    make_compensation,
)
from autoapply_agent.services.job_search import JobSearchFilters, JobSort, iter_jobs, search_jobs
from tests.unit.test_mcp_tools import call_tool

ATOM = "{http://www.w3.org/2005/Atom}"
BASE_TIME = utc_now().replace(microsecond=0) - timedelta(hours=12)
YEAR, HOUR = PayInterval.YEAR, PayInterval.HOUR
# key, title, (currency, interval, min, max, source) or None, hours after BASE_TIME
PAY_JOBS: tuple[tuple[str, str, tuple[str, PayInterval, float, float, str] | None, int], ...] = (
    ("usd-high", "Staff Engineer", ("USD", YEAR, 180_000, 220_000, "structured"), 0),
    ("usd-mid", "Senior Engineer", ("USD", YEAR, 140_000, 170_000, "description"), 1),
    ("usd-hourly", "Contract Engineer", ("USD", HOUR, 60, 75, "description"), 2),
    ("usd-tie", "Senior Engineer II", ("USD", YEAR, 120_000, 170_000, "structured"), 3),
    ("eur", "Backend Engineer", ("EUR", YEAR, 70_000, 90_000, "description"), 4),
    ("gbp", "Data Engineer", ("GBP", YEAR, 60_000, 75_000, "structured"), 5),
    ("none-1", "Platform Engineer", None, 6),
    ("none-2", "Site Reliability Engineer", None, 7),
)


async def _seed_pay(database_url: str) -> None:
    """Insert one run with the :data:`PAY_JOBS` (pay columns and ``raw.compensation``)."""

    engine = create_engine(database_url)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with create_session_factory(engine)() as session:
        session.add_all(
            [
                SourceConfig(id=1, name="seed", source_type="jsonld", base_url="https://x.test"),
                Run(id="run-pay", status=RunStatus.COMPLETED.value, query="engineer"),
            ]
        )
        await session.flush()
        for key, title, pay, hours in PAY_JOBS:
            compensation = None
            if pay is not None:
                currency, interval, low, high, source = pay
                compensation = make_compensation(
                    low, high, currency, interval, CompensationSource(source), f"{low}-{high}"
                )
            raw: dict[str, object] = {"source": "seed", "agent_decision": {"priority_tier": "high"}}
            if compensation is not None:
                raw["compensation"] = compensation.to_payload()
            session.add(
                Job(
                    run_id="run-pay",
                    source_config_id=1,
                    external_id=key,
                    title=title,
                    location="Remote - US",
                    company="Acme",
                    url=f"https://x.test/jobs/{key}",
                    score=0.8,
                    plan_steps=["Review fit"],
                    raw=raw,
                    created_at=BASE_TIME + timedelta(hours=hours),
                    **compensation_columns(compensation),
                )
            )
        await session.commit()
    await engine.dispose()


@pytest.fixture()
def pay_db(sqlite_database_url: str) -> str:
    asyncio.run(_seed_pay(sqlite_database_url))
    return sqlite_database_url


@pytest.fixture()
def client(pay_db: str) -> Iterator[TestClient]:
    settings = Settings(
        APP_NAME="Pay Test", DATABASE_URL=pay_db, ENABLE_WORKER=False, ENVIRONMENT="test"
    )
    with TestClient(create_app(settings)) as test_client:
        yield test_client


def _keys(response: Any) -> list[str]:
    assert response.status_code == 200, response.text
    return [job["external_id"] for job in response.json()]


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        # Overlap: the job's annualized maximum reaches min_salary.
        ("min_salary=160000&salary_currency=USD", {"usd-high", "usd-mid", "usd-tie"}),
        # Overlap: the job's annualized minimum is at most max_salary (hourly: 124,800).
        ("max_salary=130000&salary_currency=USD", {"usd-hourly", "usd-tie"}),
        (
            "min_salary=125000&max_salary=135000&salary_currency=USD",
            {"usd-hourly", "usd-tie"},
        ),
        (
            # Inclusive bounds; lower-case currency codes are accepted.
            "min_salary=170000&max_salary=170000&salary_currency=usd",
            {"usd-mid", "usd-tie"},
        ),
        ("salary_currency=eur", {"eur"}),
        ("salary_currency=GBP&min_salary=80000", set()),
        ("has_salary=true", {"usd-high", "usd-mid", "usd-hourly", "usd-tie", "eur", "gbp"}),
        ("has_salary=false", {"none-1", "none-2"}),
        ("has_salary=false&salary_currency=USD", set()),
    ],
)
def test_salary_filters_use_annualized_overlap_within_one_currency(
    client: TestClient, query: str, expected: set[str]
) -> None:
    assert set(_keys(client.get(f"/jobs?{query}"))) == expected


def test_jobs_expose_the_annualized_pay_columns(client: TestClient) -> None:
    (job,) = client.get("/jobs?salary_currency=USD&q=Contract").json()

    assert job["external_id"] == "usd-hourly"
    assert (job["salary_min_annual"], job["salary_max_annual"]) == (124_800, 156_000)
    assert (job["salary_currency"], job["salary_interval"]) == ("USD", "hour")
    assert job["raw"]["compensation"]["min_amount"] == 60


def test_salary_sort_is_highest_pay_first_with_newest_first_ties_and_stable_pages(
    client: TestClient,
) -> None:
    expected = ["usd-high", "usd-tie", "usd-mid", "usd-hourly"]

    full = client.get("/jobs?sort=salary&salary_currency=USD")
    pages = [
        _keys(client.get(f"/jobs?sort=salary&salary_currency=USD&limit=2&offset={offset}"))
        for offset in (0, 2)
    ]
    deduped = client.get("/jobs?sort=salary&salary_currency=USD&dedupe=true")

    assert _keys(full) == expected
    assert full.headers["X-Total-Count"] == "4"
    assert pages[0] + pages[1] == expected
    assert _keys(deduped) == expected


INVALID_SALARY_QUERIES: list[tuple[str, str, str]] = [
    ("min_salary=100000", "salary_currency", "min_salary needs salary_currency"),
    ("max_salary=100000", "salary_currency", "max_salary needs salary_currency"),
    ("sort=salary", "salary_currency", "sort=salary needs salary_currency"),
    ("salary_currency=XYZ", "salary_currency", "Unknown ISO 4217 currency code"),
    ("salary_currency=US", "salary_currency", "String should match pattern"),
    (
        "min_salary=200000&max_salary=100000&salary_currency=USD",
        "max_salary",
        "max_salary must be greater than or equal to min_salary",
    ),
    ("min_salary=-1&salary_currency=USD", "min_salary", "greater than or equal to 0"),
    (
        f"max_salary={SQLITE_MAX_INTEGER + 1}&salary_currency=USD",
        "max_salary",
        "less than or equal to",
    ),
]


@pytest.mark.parametrize(
    ("path", "query", "location", "message"),
    [
        (path, *case)
        for path in ("/jobs", "/jobs/export", "/jobs/feed.atom")
        for case in INVALID_SALARY_QUERIES
        # The feed has no sort parameter.
        if not (path == "/jobs/feed.atom" and case[0] == "sort=salary")
    ],
)
def test_invalid_salary_filters_are_422_on_every_surface(
    client: TestClient, path: str, query: str, location: str, message: str
) -> None:
    response = client.get(f"{path}?{query}")

    assert response.status_code == 422, response.text
    (error,) = response.json()["detail"]
    assert error["loc"] == ["query", location]
    assert message in error["msg"]


async def test_salary_keyset_batches_keep_nulls_last_and_match_one_query(
    pay_db: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Service level (no currency filter): batches seek past rows with and without pay."""

    monkeypatch.setattr(job_search, "_BATCH_SIZE", 2)
    engine = create_engine(pay_db)
    filters = JobSearchFilters(sort=JobSort.SALARY)
    try:
        async with create_session_factory(engine)() as session:
            streamed = [job.external_id async for job in iter_jobs(session, filters)]
            page = await search_jobs(session, filters, limit=100)
    finally:
        await engine.dispose()

    assert streamed == [job.external_id for job in page.items]
    assert streamed == [
        "usd-high",
        "usd-tie",
        "usd-mid",
        "usd-hourly",
        "eur",
        "gbp",
        "none-2",
        "none-1",
    ]


def test_csv_export_adds_stated_and_annualized_pay_columns_in_salary_order(
    client: TestClient,
) -> None:
    response = client.get("/jobs/export?format=csv&sort=salary&salary_currency=USD")

    assert response.status_code == 200, response.text
    rows = list(csv.DictReader(io.StringIO(response.text)))
    assert [row["external_id"] for row in rows] == ["usd-high", "usd-tie", "usd-mid", "usd-hourly"]
    hourly = {key: value for key, value in rows[-1].items() if key.startswith("salary_")}
    assert hourly == {
        "salary_min": "60",
        "salary_max": "75",
        "salary_interval": "hour",
        "salary_currency": "USD",
        "salary_min_annual": "124800",
        "salary_max_annual": "156000",
        "salary_source": "description",
    }
    unpaid = client.get("/jobs/export?format=csv&has_salary=false").text
    assert all(
        row[key] == ""
        for row in csv.DictReader(io.StringIO(unpaid))
        for key in row
        if key.startswith("salary_")
    )


def test_jsonl_export_carries_the_pay_columns_and_range(client: TestClient) -> None:
    response = client.get("/jobs/export?format=jsonl&salary_currency=EUR")

    (record,) = [json.loads(line) for line in response.text.splitlines()]
    assert (record["salary_min_annual"], record["salary_max_annual"]) == (70_000, 90_000)
    assert record["raw"]["compensation"]["source"] == "description"


def test_atom_feed_summaries_state_the_pay_range(client: TestClient) -> None:
    response = client.get("/jobs/feed.atom?salary_currency=USD&max_salary=125000")

    assert response.status_code == 200, response.text
    feed = ET.fromstring(response.content)
    assert "max_salary=125000, salary_currency=USD" in (feed.findtext(f"{ATOM}title") or "")
    summaries = {
        entry.findtext(f"{ATOM}title"): entry.findtext(f"{ATOM}summary")
        for entry in feed.iter(f"{ATOM}entry")
    }
    assert summaries == {
        "Senior Engineer II at Acme": (
            "Company: Acme | Location: Remote - US | Remote: yes | "
            "Pay: USD 120,000\u2013170,000 per year | Score: 0.80 | Priority: high"
        ),
        "Contract Engineer at Acme": (
            "Company: Acme | Location: Remote - US | Remote: yes | "
            "Pay: USD 60\u201375 per hour (USD 124,800\u2013156,000 per year) | "
            "Score: 0.80 | Priority: high"
        ),
    }


RESUME = "Senior engineer: Python, Kubernetes, PostgreSQL."


def test_match_ranks_only_jobs_inside_the_salary_filters(client: TestClient) -> None:
    response = client.post(
        "/jobs/match",
        json={"resume_text": RESUME, "salary_currency": "usd", "min_salary": 160000},
    )

    assert response.status_code == 200, response.text
    jobs = response.json()["jobs"]
    assert {job["external_id"] for job in jobs} == {"usd-high", "usd-mid", "usd-tie"}
    assert all(job["salary_currency"] == "USD" for job in jobs)
    csv_text = client.post(
        "/jobs/match?format=csv", json={"resume_text": RESUME, "has_salary": False}
    ).text
    assert {row["external_id"] for row in csv.DictReader(io.StringIO(csv_text))} == {
        "none-1",
        "none-2",
    }


@pytest.mark.parametrize(
    ("body", "location", "message"),
    [
        ({"min_salary": 1}, "salary_currency", "min_salary needs salary_currency"),
        ({"salary_currency": "ABC"}, "salary_currency", "Unknown ISO 4217 currency code"),
        (
            {"salary_currency": "USD", "min_salary": 2, "max_salary": 1},
            "max_salary",
            "max_salary must be greater than or equal to min_salary",
        ),
    ],
)
def test_match_rejects_invalid_salary_filters_without_echoing_the_resume(
    client: TestClient, body: dict[str, Any], location: str, message: str
) -> None:
    response = client.post("/jobs/match", json={"resume_text": RESUME, **body})

    assert response.status_code == 422, response.text
    (error,) = response.json()["detail"]
    assert error["loc"] == ["body", location]
    assert message in error["msg"]
    assert RESUME not in response.text


async def test_mcp_search_jobs_filters_sorts_and_reports_pay(pay_db: str) -> None:
    engine, session_factory = open_read_only_database(pay_db)
    try:
        server = CareerSearchMcpServer(session_factory)
        result = await call_tool(
            server,
            "search_jobs",
            {"salary_currency": "USD", "min_salary": 150000, "sort": "salary", "limit": 2},
        )
        detail = await call_tool(server, "get_job", {"job_id": 3})
        unpaid = await call_tool(server, "get_job", {"job_id": 7})
    finally:
        await engine.dispose()

    assert result["isError"] is False, result["content"][0]["text"]
    content = result["structuredContent"]
    assert [job["title"] for job in content["jobs"]] == ["Staff Engineer", "Senior Engineer II"]
    assert (content["total"], content["sort"]) == (4, "salary")
    assert content["jobs"][0]["pay"] == {
        "min_amount": 180_000,
        "max_amount": 220_000,
        "currency": "USD",
        "interval": "year",
        "annual_min": 180_000,
        "annual_max": 220_000,
        "source": "structured",
    }
    assert (
        "Staff Engineer — Acme · Remote - US · USD 180,000-220,000/yr"
        in (result["content"][0]["text"])
    )
    assert detail["structuredContent"]["job"]["pay"]["interval"] == "hour"
    assert (
        "Pay: USD 60\u201375 per hour (USD 124,800\u2013156,000 per year) (from the posting's "
        "description data; informational)" in detail["content"][0]["text"]
    )
    assert unpaid["structuredContent"]["job"]["pay"] is None
    assert "Pay: not stated in the captured posting" in unpaid["content"][0]["text"]


MCP_INVALID_SALARY_ARGUMENTS: list[tuple[dict[str, Any], str]] = [
    ({"min_salary": 1}, "min_salary needs salary_currency"),
    ({"sort": "salary"}, "sort=salary needs salary_currency"),
    ({"salary_currency": "XYZ"}, "'XYZ' is not an ISO 4217 currency code"),
    ({"salary_currency": "usd", "min_salary": 9, "max_salary": 1}, "max_salary must be"),
]


@pytest.mark.parametrize(
    ("tool", "arguments", "message"),
    [
        (tool, arguments, message)
        for tool in ("search_jobs", "match_resume_to_jobs")
        for arguments, message in MCP_INVALID_SALARY_ARGUMENTS
        # match_resume_to_jobs has its own sort (match or blend).
        if not (tool == "match_resume_to_jobs" and "sort" in arguments)
    ],
)
async def test_mcp_invalid_salary_arguments_are_tool_errors(
    pay_db: str, tool: str, arguments: dict[str, Any], message: str
) -> None:
    if tool == "match_resume_to_jobs":
        arguments = {**arguments, "resume_text": RESUME}
    engine, session_factory = open_read_only_database(pay_db)
    try:
        result = await call_tool(CareerSearchMcpServer(session_factory), tool, arguments)
    finally:
        await engine.dispose()

    assert result["isError"] is True
    assert message in result["content"][0]["text"]

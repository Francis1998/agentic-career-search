"""API tests for ``POST /jobs/match``: ranking, filters, limits, privacy and CSV."""

from __future__ import annotations

import asyncio
import csv
import hashlib
import io
import json
import logging
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from autoapply_agent.core.config import Settings
from autoapply_agent.core.time import utc_now
from autoapply_agent.db.base import Base
from autoapply_agent.db.models import Job, Run, RunStatus, SourceConfig
from autoapply_agent.db.session import create_engine, create_session_factory
from autoapply_agent.main import create_app
from autoapply_agent.services.resume_match import MATCH_CSV_COLUMNS, MAX_RESUME_CHARS

if TYPE_CHECKING:
    from _pytest.logging import LogCaptureFixture

BASE_TIME = utc_now().replace(microsecond=0) - timedelta(hours=10, minutes=30)
CANARY = "CANARY-7f3a"
RESUME = f"{CANARY}\nSenior engineer: Python, FastAPI, Postgres, Docker, k8s, AWS, Terraform, Helm."


@dataclass(frozen=True)
class MatchJob:
    """One job row to insert before the app starts."""

    key: str
    run_id: str
    source_config_id: int
    title: str
    company: str | None
    location: str | None
    url: str
    score: float
    hours_after_base: int
    description: str | None = None


ACME_DESCRIPTION = (
    "Python, FastAPI, PostgreSQL, Docker and Kubernetes on AWS. Nice to have: Go, Kafka."
)
MATCH_JOBS = (
    MatchJob(
        "acme",
        "run-a",
        1,
        "Senior Python Engineer",
        "Acme Robotics",
        "Remote - US",
        "https://boards.greenhouse.io/acme/jobs/1",
        0.92,
        0,
        ACME_DESCRIPTION,
    ),
    MatchJob(
        "hooli",
        "run-a",
        2,
        "Data Engineer",
        "Hooli",
        "Berlin, Germany",
        "https://jobs.lever.co/hooli/data",
        0.55,
        1,
        "Spark, Airflow and SQL on GCP.",
    ),
    MatchJob(
        "initech",
        "run-a",
        1,
        "Backend Engineer, Payments",
        "Initech",
        "New York, NY",
        "https://boards.greenhouse.io/initech/jobs/3",
        0.71,
        2,
        "Java, Spring Boot, PostgreSQL and Kafka.",
    ),
    MatchJob(
        "globex",
        "run-b",
        2,
        "Staff Platform Engineer (Python, Kubernetes)",
        "Globex",
        "Anywhere",
        "https://jobs.lever.co/globex/platform",
        0.88,
        3,
        "Terraform, Helm and Argo CD on AWS; Go tooling.",
    ),
    # Cross-board mirror of "acme": dedupe (on by default) keeps only the first capture.
    MatchJob(
        "acme-mirror",
        "run-b",
        2,
        "Senior Python Engineer",
        "Acme Robotics, Inc.",
        "Remote - US",
        "https://jobs.lever.co/acme/py",
        0.9,
        4,
        ACME_DESCRIPTION,
    ),
    MatchJob(
        "sre",
        "run-b",
        1,
        "Site Reliability Engineer",
        None,
        None,
        "https://boards.greenhouse.io/unknown/jobs/7",
        0.4,
        5,
    ),
)
# Match scores with RESUME: acme 6/8, globex 5/8, hooli 1/5 (sql via postgresql),
# initech 1/6, sre 0/1.
RANKED_BY_MATCH = ["acme", "globex", "hooli", "initech", "sre"]

# Tie-breaks for a resume naming Python and Docker.
TIE_JOBS = (
    MatchJob("one-of-two", "run-a", 1, "Engineer", "A", "Remote", "https://a.example/1", 0.95, 0,
             "Python and Go."),
    MatchJob("two-of-four", "run-a", 1, "Engineer", "B", "Remote", "https://b.example/1", 0.5, 0,
             "Python, Docker, Go and Rust."),
    MatchJob("full-old", "run-a", 1, "Engineer", "C", "Remote", "https://c.example/1", 0.6, 0,
             "Python."),
    MatchJob("full-same-a", "run-a", 1, "Engineer", "D", "Remote", "https://d.example/1", 0.6, 1,
             "Python."),
    MatchJob("full-same-b", "run-a", 1, "Engineer", "E", "Remote", "https://e.example/1", 0.6, 1,
             "Python."),
    MatchJob("full-new", "run-a", 1, "Engineer", "F", "Remote", "https://f.example/1", 0.6, 2,
             "Python."),
    MatchJob("full-high", "run-a", 1, "Engineer", "G", "Remote", "https://g.example/1", 0.7, 0,
             "Docker."),
)  # fmt: skip

HOSTILE_JOBS = (
    MatchJob(
        "hostile",
        "run-a",
        1,
        '=HYPERLINK("https://evil.example","Apply here")',
        "Injected Co",
        "-1+1",
        "javascript:alert(1)",
        0.31,
        0,
        "@SUM(1+1) Python",
    ),
)


async def _seed(database_url: str, jobs: tuple[MatchJob, ...]) -> None:
    """Create the schema and insert runs, source configs and jobs with descriptions."""

    engine = create_engine(database_url)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with create_session_factory(engine)() as session:
        session.add_all(
            [
                SourceConfig(
                    id=1, name="seed-greenhouse", source_type="greenhouse", base_url="https://g.io"
                ),
                SourceConfig(id=2, name="seed-lever", source_type="lever", base_url="https://l.co"),
                Run(id="run-a", status=RunStatus.COMPLETED.value, query="python"),
                Run(id="run-b", status=RunStatus.COMPLETED.value, query="platform"),
            ]
        )
        await session.flush()
        for job in jobs:
            raw: dict[str, object] = {"source": "seed", "agent_decision": {"priority_tier": "high"}}
            if job.description is not None:
                raw["description"] = job.description
            session.add(
                Job(
                    run_id=job.run_id,
                    source_config_id=job.source_config_id,
                    external_id=job.key,
                    title=job.title,
                    location=job.location,
                    company=job.company,
                    url=job.url,
                    score=job.score,
                    plan_steps=["Review fit"],
                    raw=raw,
                    created_at=BASE_TIME + timedelta(hours=job.hours_after_base),
                )
            )
            await session.flush()
        await session.commit()
    await engine.dispose()


def app_client(database_url: str) -> Iterator[TestClient]:
    """Yield a client for an app without a background worker."""

    settings = Settings(DATABASE_URL=database_url, ENABLE_WORKER=False, ENVIRONMENT="test")
    with TestClient(create_app(settings)) as client:
        yield client


def client_for(database_url: str, jobs: tuple[MatchJob, ...]) -> Iterator[TestClient]:
    """Seed the database, then yield a client."""

    asyncio.run(_seed(database_url, jobs))
    yield from app_client(database_url)


@pytest.fixture()
def client(sqlite_database_url: str) -> Iterator[TestClient]:
    """Client over :data:`MATCH_JOBS`."""

    yield from client_for(sqlite_database_url, MATCH_JOBS)


def match(client: TestClient, **body: Any) -> dict[str, Any]:
    """POST /jobs/match with :data:`RESUME` (unless given) and return the JSON body."""

    response = client.post("/jobs/match", json={"resume_text": RESUME, **body})
    assert response.status_code == 200, response.text
    assert response.headers["x-total-count"] == str(response.json()["total"])
    result: dict[str, Any] = response.json()
    return result


def keys(result: dict[str, Any]) -> list[str]:
    """External ids of the ranked jobs, best first."""

    return [job["external_id"] for job in result["jobs"]]


# ---------------------------------------------------------------------------
# Ranking
# ---------------------------------------------------------------------------


def test_ranks_by_match_with_matched_missing_skills_and_explanations(client: TestClient) -> None:
    result = match(client)

    assert keys(result) == RANKED_BY_MATCH
    assert result["total"] == 5
    assert result["sort"] == "match"
    assert result["resume_sha256"] == hashlib.sha256(RESUME.encode()).hexdigest()
    assert result["resume_skills"] == [
        "aws",
        "docker",
        "fastapi",
        "helm",
        "kubernetes",
        "postgresql",
        "python",
        "terraform",
    ]
    assert result["implied_skills"] == {
        "infrastructure as code": ["terraform"],
        "sql": ["postgresql"],
    }
    acme, globex = result["jobs"][:2]
    assert (acme["rank"], acme["match_score"], acme["blend_score"]) == (1, 0.75, 0.801)
    assert acme["matched_skills"] == [
        "python",
        "fastapi",
        "postgresql",
        "docker",
        "kubernetes",
        "aws",
    ]
    assert acme["missing_skills"] == ["go", "kafka"]
    assert acme["extra_skills"] is None
    assert acme["explanation"] == (
        "Matches 6 of 8 skills in this posting: python, fastapi, postgresql, docker, "
        "kubernetes, aws. Missing: go, kafka."
    )
    # Job fields come through unchanged.
    assert (acme["title"], acme["company"], acme["score"]) == (
        "Senior Python Engineer",
        "Acme Robotics",
        0.92,
    )
    assert acme["raw"]["agent_decision"] == {"priority_tier": "high"}
    assert globex["matched_skills"] == ["python", "kubernetes", "terraform", "helm", "aws"]
    assert globex["missing_skills"] == ["platform engineering", "argo cd", "go"]
    assert result["jobs"][-1]["explanation"] == (
        "Matches none of the 1 skill in this posting. Missing: site reliability engineering."
    )


def test_implied_skills_count_as_matched_and_are_explained(client: TestClient) -> None:
    result = match(client, resume_text="PostgreSQL and Apache Spark", q="data")

    hooli = result["jobs"][0]
    assert hooli["matched_skills"] == ["spark", "sql"]
    assert hooli["match_score"] == 0.4
    assert "spark, sql (via postgresql)." in hooli["explanation"]


def test_blend_mixes_in_the_deterministic_score(client: TestClient) -> None:
    result = match(client, sort="blend")

    assert result["sort"] == "blend"
    assert keys(result) == ["acme", "globex", "initech", "hooli", "sre"]  # hooli's low score
    blends = [job["blend_score"] for job in result["jobs"]]
    assert blends == sorted(blends, reverse=True)
    assert all(
        job["blend_score"] == round(0.7 * job["match_score"] + 0.3 * job["score"], 4)
        for job in result["jobs"]
    )
    assert result["jobs"][0]["explanation"].endswith(
        "Blend 0.8010 = 0.7 * match 0.7500 + 0.3 * score 0.9200."
    )


@pytest.mark.parametrize(
    ("sort", "expected"),
    [
        (
            "match",
            [
                "full-high",
                "full-new",
                "full-same-b",
                "full-same-a",
                "full-old",
                "two-of-four",
                "one-of-two",
            ],
        ),
        (
            "blend",
            [
                "full-high",
                "full-new",
                "full-same-b",
                "full-same-a",
                "full-old",
                "one-of-two",
                "two-of-four",
            ],
        ),
    ],
)
def test_ties_break_deterministically(
    sqlite_database_url: str, sort: str, expected: list[str]
) -> None:
    for client in client_for(sqlite_database_url, TIE_JOBS):
        first = match(client, resume_text="Python and Docker", sort=sort)
        again = match(client, resume_text="Python and Docker", sort=sort)

        assert keys(first) == expected
        assert first == again


def test_limit_min_match_and_extra_skills(client: TestClient) -> None:
    top = match(client, limit=2, include_extra_skills=True)
    strong = match(client, min_match=0.5)

    assert (keys(top), top["total"]) == (["acme", "globex"], 5)
    assert top["jobs"][0]["extra_skills"] == ["helm", "terraform"]
    assert keys(strong) == ["acme", "globex"]
    assert strong["total"] == 2


def test_resume_without_known_skills_ranks_everything_at_zero(client: TestClient) -> None:
    result = match(client, resume_text="I enjoy gardening and long walks.")

    assert result["resume_skills"] == []
    assert {job["match_score"] for job in result["jobs"]} == {0.0}
    assert keys(result)[:2] == ["acme", "globex"]  # Ties fall back to the stored score.


# ---------------------------------------------------------------------------
# Filters: the GET /jobs code path
# ---------------------------------------------------------------------------

FILTER_CASES: list[dict[str, Any]] = [
    {},
    {"q": "python"},
    {"q": "engineer remote"},
    {"company": "acme"},
    {"location": "new york"},
    {"remote": True},
    {"remote": False},
    {"min_score": 0.8},
    {"source_config_id": 2},
    {"run_id": "run-b"},
    {"hours_old": 8},
    {"created_after": (BASE_TIME + timedelta(hours=3)).isoformat()},
    {"dedupe": False},
    {"q": "engineer", "remote": True, "min_score": 0.85, "dedupe": False},
]


@pytest.mark.parametrize("filters", FILTER_CASES, ids=[json.dumps(c) for c in FILTER_CASES])
def test_filters_select_exactly_what_get_jobs_selects(
    client: TestClient, filters: dict[str, Any]
) -> None:
    dedupe = filters.get("dedupe", True)
    params = {
        key: str(value).lower() if isinstance(value, bool) else str(value)
        for key, value in {**filters, "dedupe": dedupe}.items()
    }
    listed = client.get("/jobs", params={**params, "limit": "500"})
    assert listed.status_code == 200, listed.text

    result = match(client, **filters, limit=500)

    assert sorted(keys(result)) == sorted(job["external_id"] for job in listed.json())
    assert result["total"] == int(listed.headers["x-total-count"])


# ---------------------------------------------------------------------------
# Validation and size limits
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("body", "error_type", "location"),
    [
        ({"resume_text": CANARY + "x" * MAX_RESUME_CHARS}, "string_too_long", "resume_text"),
        ({"resume_text": " \n\t "}, "resume_blank", "resume_text"),
        ({}, "missing", "resume_text"),
        ({"resume_text": RESUME, "notes": CANARY}, "extra_forbidden", "notes"),
        ({"resume_text": RESUME, "sort": "salary"}, "literal_error", "sort"),
        ({"resume_text": RESUME, "limit": 501}, "less_than_equal", "limit"),
        ({"resume_text": RESUME, "min_match": 1.5}, "less_than_equal", "min_match"),
        (
            {"resume_text": RESUME, "created_after": "0001-01-01T00:00:00+01:00"},
            "datetime_utc_range",
            "created_after",
        ),
    ],
)
def test_invalid_bodies_are_422_without_echoing_input(
    client: TestClient, body: dict[str, Any], error_type: str, location: str
) -> None:
    response = client.post("/jobs/match", json=body)

    assert response.status_code == 422
    errors = response.json()["detail"]
    assert [(error["type"], error["loc"]) for error in errors] == [(error_type, ["body", location])]
    assert "input" not in errors[0]
    assert CANARY not in response.text and "Senior engineer" not in response.text


def test_malformed_json_and_empty_bodies_are_422(client: TestClient) -> None:
    malformed = client.post(
        "/jobs/match",
        content=f'{{"resume_text": "{CANARY}'.encode(),
        headers={"content-type": "application/json"},
    )
    empty = client.post("/jobs/match", content=b"", headers={"content-type": "application/json"})

    assert malformed.status_code == 422
    assert malformed.json()["detail"][0]["type"] == "json_invalid"
    assert CANARY not in malformed.text
    assert empty.status_code == 422
    assert empty.json()["detail"] == [{"type": "missing", "loc": ["body"], "msg": "Field required"}]


def test_oversized_bodies_are_413_with_or_without_content_length(client: TestClient) -> None:
    oversized = json.dumps({"resume_text": "a" * (1024 * 1024)}).encode()

    def chunks() -> Iterator[bytes]:
        for start in range(0, len(oversized), 64 * 1024):
            yield oversized[start : start + 64 * 1024]

    declared = client.post(
        "/jobs/match", content=oversized, headers={"content-type": "application/json"}
    )
    streamed = client.post(
        "/jobs/match", content=chunks(), headers={"content-type": "application/json"}
    )

    for response in (declared, streamed):
        assert response.status_code == 413
        assert response.json() == {
            "detail": "Request body exceeds 1048576 bytes; resume_text is limited to 50000 "
            "characters."
        }


def test_any_resume_within_the_character_limit_fits_the_body_limit(client: TestClient) -> None:
    # Astral characters are the worst case: 12 bytes each as JSON \\u escapes.
    resume = "Python " + "\U0001f600" * (MAX_RESUME_CHARS - 7)
    body = json.dumps({"resume_text": resume}).encode()

    response = client.post(
        "/jobs/match", content=body, headers={"content-type": "application/json"}
    )

    assert len(body) > 512 * 1024
    assert response.status_code == 200, response.text
    assert response.json()["resume_skills"] == ["python"]


def test_non_json_bodies_are_415(client: TestClient) -> None:
    response = client.post("/jobs/match", data={"resume_text": RESUME})

    assert response.status_code == 415
    assert CANARY not in response.text


# ---------------------------------------------------------------------------
# Privacy: never logged, never persisted
# ---------------------------------------------------------------------------


def test_resume_text_is_never_logged(client: TestClient, caplog: LogCaptureFixture) -> None:
    digest = hashlib.sha256(RESUME.encode()).hexdigest()

    with caplog.at_level(logging.DEBUG):
        match(client)
        client.post("/jobs/match?format=csv", json={"resume_text": RESUME})
        client.post("/jobs/match", json={"resume_text": RESUME, "limit": 0})
        client.post("/jobs/match", json={"resume_text": CANARY + "x" * MAX_RESUME_CHARS})

    logged = "\n".join(
        f"{record.name} {record.getMessage()} {record.args!r}" for record in caplog.records
    )
    assert f"jobs_match resume_sha256={digest}" in logged
    assert CANARY not in logged
    assert "Senior engineer" not in logged


def test_resume_text_is_never_persisted(client: TestClient, sqlite_database_url: str) -> None:
    database = Path(sqlite_database_url.removeprefix("sqlite+aiosqlite:///"))

    async def table_counts() -> dict[str, int]:
        engine = create_engine(sqlite_database_url)
        try:
            async with engine.connect() as connection:
                return {
                    table: (
                        await connection.execute(text(f"SELECT count(*) FROM {table}"))
                    ).scalar_one()
                    for table in Base.metadata.tables
                }
        finally:
            await engine.dispose()

    before = asyncio.run(table_counts())
    match(client)
    client.post("/jobs/match?format=csv", json={"resume_text": RESUME})

    assert asyncio.run(table_counts()) == before
    for path in database.parent.iterdir():
        assert CANARY.encode() not in path.read_bytes(), path.name


# ---------------------------------------------------------------------------
# CSV and OpenAPI
# ---------------------------------------------------------------------------


def test_csv_output_is_spreadsheet_safe(sqlite_database_url: str) -> None:
    for client in client_for(sqlite_database_url, (*MATCH_JOBS, *HOSTILE_JOBS)):
        response = client.post(
            "/jobs/match?format=csv", json={"resume_text": RESUME, "include_extra_skills": True}
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        assert response.headers["x-total-count"] == "6"
        disposition = response.headers["content-disposition"]
        assert disposition.startswith('attachment; filename="job-matches-')
        rows = list(csv.reader(io.StringIO(response.text)))
        assert tuple(rows[0]) == MATCH_CSV_COLUMNS
        records = [dict(zip(MATCH_CSV_COLUMNS, row, strict=True)) for row in rows[1:]]
        assert [record["external_id"] for record in records] == ["hostile", *RANKED_BY_MATCH]
        hostile = records[0]
        assert hostile["title"].startswith("'=HYPERLINK")
        assert (hostile["location"], hostile["url"]) == ("'-1+1", "")
        assert (hostile["match_score"], hostile["matched_skills"]) == ("1.0", "python")
        assert records[1]["missing_skills"] == "go; kafka"
        assert records[1]["extra_skills"] == "helm; terraform"
        assert response.text.endswith("\r\n")

        assert (
            client.post("/jobs/match?format=xml", json={"resume_text": RESUME}).status_code == 422
        )


def test_openapi_documents_the_json_body(client: TestClient) -> None:
    operation = client.get("/openapi.json").json()["paths"]["/jobs/match"]["post"]

    body = operation["requestBody"]
    schema = body["content"]["application/json"]["schema"]
    assert body["required"] is True
    assert schema["required"] == ["resume_text"]
    assert schema["properties"]["resume_text"]["maxLength"] == MAX_RESUME_CHARS
    assert schema["additionalProperties"] is False
    assert {"413", "415", "422"} <= set(operation["responses"])

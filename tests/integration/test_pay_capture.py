"""Pay captured by discovery: JSON-LD fixture page -> worker -> salary columns and raw."""

from __future__ import annotations

import json
import time
from typing import Any

import pytest
from fastapi.testclient import TestClient

from autoapply_agent.adapters.jsonld import JsonLdAdapter
from autoapply_agent.core.config import Settings
from autoapply_agent.main import create_app

POSTINGS: list[dict[str, Any]] = [
    {
        "@type": "JobPosting",
        "title": "Staff Data Engineer",
        "url": "https://acme.example.com/jobs/structured",
        "baseSalary": {
            "@type": "MonetaryAmount",
            "currency": "USD",
            "value": {"minValue": 180000, "maxValue": 220000, "unitText": "YEAR"},
        },
    },
    {
        "@type": "JobPosting",
        "title": "Support Engineer",
        "url": "https://acme.example.com/jobs/hourly",
        "description": "&lt;p&gt;Hourly rate: $40 - $48 plus overtime.&lt;/p&gt;",
    },
    {
        "@type": "JobPosting",
        "title": "Platform Engineer",
        "url": "https://acme.example.com/jobs/no-pay",
        "description": "<p>Competitive salary and a $500 home office stipend.</p>",
    },
]


async def _fixture_page(
    self: JsonLdAdapter, base_url: str, timeout_seconds: float, user_agent: str
) -> str:
    """Serve the fixture postings instead of fetching ``base_url``."""

    del self, base_url, timeout_seconds, user_agent
    return f'<script type="application/ld+json">{json.dumps(POSTINGS)}</script>'


def test_discovery_persists_pay_columns_and_the_full_range_in_raw(
    sqlite_database_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(JsonLdAdapter, "_request_html", _fixture_page)
    settings = Settings(
        APP_NAME="pay-capture-test",
        DATABASE_URL=sqlite_database_url,
        WORKER_POLL_INTERVAL_SECONDS=0.05,
        ENABLE_WORKER=True,
        ENVIRONMENT="test",
    )
    with TestClient(create_app(settings)) as client:
        source = client.post(
            "/source-configs",
            json={"name": "acme", "source_type": "jsonld", "base_url": "https://acme.example.com"},
        )
        assert source.status_code == 201, source.text
        run_id = client.post("/runs", json={"query": "engineer"}).json()["id"]
        for _ in range(100):
            if client.get(f"/runs/{run_id}").json()["status"] in {"completed", "failed"}:
                break
            time.sleep(0.05)
        jobs = {job["title"]: job for job in client.get(f"/jobs?run_id={run_id}").json()}

    columns = ("salary_min_annual", "salary_max_annual", "salary_currency", "salary_interval")
    assert {title: tuple(job[name] for name in columns) for title, job in jobs.items()} == {
        "Staff Data Engineer": (180_000, 220_000, "USD", "year"),
        "Support Engineer": (83_200, 99_840, "USD", "hour"),
        "Platform Engineer": (None, None, None, None),
    }
    hourly = jobs["Support Engineer"]["raw"]["compensation"]
    assert hourly == {
        "min_amount": 40,
        "max_amount": 48,
        "currency": "USD",
        "interval": "hour",
        "annual_min": 83_200,
        "annual_max": 99_840,
        "source": "description",
        "snippet": "$40 - $48",
    }
    assert jobs["Staff Data Engineer"]["raw"]["compensation"]["source"] == "structured"
    assert "compensation" not in jobs["Platform Engineer"]["raw"]

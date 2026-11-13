"""Resume match service: profile privacy, job text, coverage, explanations and CSV."""

from __future__ import annotations

import csv
import hashlib
import io
from datetime import UTC, datetime

from autoapply_agent.db.models import Job
from autoapply_agent.services.resume_match import (
    MATCH_CSV_COLUMNS,
    MAX_JOB_TEXT_CHARS,
    MatchPage,
    MatchSort,
    RankedJob,
    ResumeProfile,
    blend_score,
    explain_match,
    job_match_text,
    match_skills,
    render_match_csv,
)
from autoapply_agent.services.skill_extraction import extract_skills

RESUME = "CANARY-7f3a Senior engineer: Python, Postgres, k8s and Terraform."


def _job(**fields: object) -> Job:
    """A transient job with sensible defaults."""

    values: dict[str, object] = {
        "id": 1,
        "run_id": "run-a",
        "source_config_id": 1,
        "external_id": "ext-1",
        "title": "Platform Engineer",
        "company": "Acme",
        "location": "Remote",
        "url": "https://example.com/jobs/1",
        "score": 0.8,
        "plan_steps": [],
        "raw": None,
        "created_at": datetime(2026, 11, 12, 8, 0, tzinfo=UTC),
    }
    values.update(fields)
    return Job(**values)


def test_profile_keeps_a_digest_and_skills_but_never_the_text() -> None:
    profile = ResumeProfile.from_text(RESUME)

    assert profile.sha256 == hashlib.sha256(RESUME.encode()).hexdigest()
    assert profile.characters == len(RESUME)
    assert profile.skills == ("kubernetes", "postgresql", "python", "terraform")
    assert profile.implied == {"infrastructure as code": ("terraform",), "sql": ("postgresql",)}
    assert profile.known == {*profile.skills, "infrastructure as code", "sql"}
    assert "CANARY" not in repr(profile)


def test_job_text_reads_title_then_description_fields_without_markup() -> None:
    job = _job(
        title="Data Engineer",
        company="Snowflake Inc",
        location="Go, Remote",
        raw={
            "source": "jsonld",
            "description": "<p>Build pipelines in <b>Python</b> &amp; SQL</p>",
            "skills": ["Airflow", 42, "dbt"],
            "llm_enrichment": {"summary": "Needs Kafka"},
        },
    )

    text = job_match_text(job)

    assert text.splitlines()[0] == "Data Engineer"
    assert "Build pipelines in  Python  & SQL" in text
    assert "Snowflake" not in text and "Go" not in text and "Kafka" not in text
    assert extract_skills(text) == ["data engineering", "python", "sql", "airflow", "dbt"]


def test_job_text_is_capped() -> None:
    job = _job(raw={"description": "x" * (3 * MAX_JOB_TEXT_CHARS), "requirements": "Python"})

    assert len(job_match_text(job)) == MAX_JOB_TEXT_CHARS
    assert job_match_text(_job(raw=["not", "a", "dict"])) == "Platform Engineer"


def test_coverage_keeps_posting_order_and_credits_implied_skills() -> None:
    profile = ResumeProfile.from_text(RESUME)

    match = match_skills(["sql", "go", "python", "kubernetes"], profile)

    assert match.match_score == 0.75
    assert match.matched == ("sql", "python", "kubernetes")
    assert match.missing == ("go",)
    assert match.extra == ("postgresql", "terraform")
    assert explain_match(match, profile, score=0.8) == (
        "Matches 3 of 4 skills in this posting: sql (via postgresql), python, kubernetes. "
        "Missing: go."
    )


def test_explanations_for_empty_and_unmatched_postings_and_blends() -> None:
    profile = ResumeProfile.from_text(RESUME)
    nothing = match_skills([], profile)
    unmatched = match_skills(["rust"], profile)

    assert nothing.match_score == 0.0
    assert explain_match(nothing, profile, score=0.5).startswith("No skills from the lexicon")
    assert explain_match(unmatched, profile, score=0.5, blend=0.15) == (
        "Matches none of the 1 skill in this posting. Missing: rust. "
        "Blend 0.1500 = 0.7 * match 0.0000 + 0.3 * score 0.5000."
    )
    assert blend_score(0.75, 0.8) == 0.765


def test_csv_reuses_the_export_columns_and_neutralizes_formulas() -> None:
    profile = ResumeProfile.from_text(RESUME)
    job = _job(title='=HYPERLINK("https://evil.example")', location="-1+1", url="javascript:x")
    match = match_skills(["python", "go"], profile)
    page = MatchPage(
        total=1,
        sort=MatchSort.MATCH,
        items=[RankedJob(1, job, match, 0.59, "@explanation")],
    )

    plain = list(csv.reader(io.StringIO(render_match_csv(page, include_extra_skills=False))))
    extra = list(csv.reader(io.StringIO(render_match_csv(page, include_extra_skills=True))))

    assert tuple(plain[0]) == MATCH_CSV_COLUMNS
    row = dict(zip(MATCH_CSV_COLUMNS, plain[1], strict=True))
    assert row["rank"] == "1" and row["match_score"] == "0.5" and row["blend_score"] == "0.59"
    assert (row["matched_skills"], row["missing_skills"], row["extra_skills"]) == (
        "python",
        "go",
        "",
    )
    assert row["explanation"] == "'@explanation"
    assert row["title"].startswith("'=HYPERLINK")
    assert (row["location"], row["url"]) == ("'-1+1", "")
    assert dict(zip(MATCH_CSV_COLUMNS, extra[1], strict=True))["extra_skills"] == (
        "kubernetes; postgresql; terraform"
    )

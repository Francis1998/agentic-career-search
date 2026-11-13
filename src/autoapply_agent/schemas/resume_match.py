"""Pydantic schemas for ``POST /jobs/match`` (resume-to-job match)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic_core import PydanticCustomError

from autoapply_agent.db.models import SQLITE_MAX_INTEGER
from autoapply_agent.schemas.jobs import JobRead
from autoapply_agent.services.resume_match import MAX_RESUME_CHARS


class ResumeMatchRequest(BaseModel):
    """JSON body of ``POST /jobs/match``: resume text plus the ``GET /jobs`` filters."""

    model_config = ConfigDict(extra="forbid")

    resume_text: str = Field(
        min_length=1,
        max_length=MAX_RESUME_CHARS,
        description="Plain text of the resume (convert PDF/DOCX first). Used in memory "
        "only: never stored or logged; only its SHA-256 digest is logged.",
    )
    q: str | None = Field(
        default=None,
        max_length=200,
        description="Space-separated terms; each must match title, company or location.",
    )
    company: str | None = Field(
        default=None, max_length=256, description="Case-insensitive company substring."
    )
    location: str | None = Field(
        default=None, max_length=256, description="Case-insensitive location substring."
    )
    remote: bool | None = Field(
        default=None,
        description="true: location mentions remote, anywhere, work from home, wfh, "
        "telecommute or distributed; false: it does not (or is empty).",
    )
    min_score: float | None = Field(
        default=None, ge=0.0, le=1.0, description="Minimum deterministic score (inclusive)."
    )
    source_config_id: int | None = Field(
        default=None,
        ge=1,
        le=SQLITE_MAX_INTEGER,
        description="Only jobs captured from this source config.",
    )
    run_id: str | None = Field(
        default=None, min_length=1, max_length=64, description="Only jobs captured by this run."
    )
    created_after: datetime | None = Field(
        default=None,
        description="ISO-8601 instant; only jobs captured at or after it (naive means UTC).",
    )
    hours_old: int | None = Field(
        default=None,
        ge=1,
        le=8760,
        description="Only jobs captured within the last N hours (like JobSpy hours_old).",
    )
    dedupe: bool = Field(
        default=True,
        description="Rank each posting once: collapse re-captures of one URL and "
        "cross-board mirrors (first capture wins). Unlike GET /jobs, on by default.",
    )
    sort: Literal["match", "blend"] = Field(
        default="match",
        description="match: highest match score first (ties: more matched skills, higher "
        "score, newer); blend: 0.7 * match score + 0.3 * deterministic score.",
    )
    limit: int = Field(default=20, ge=1, le=500, description="Number of top jobs returned.")
    min_match: float | None = Field(
        default=None, ge=0.0, le=1.0, description="Drop jobs whose match score is lower."
    )
    include_extra_skills: bool = Field(
        default=False,
        description="Also list, per job, the resume skills the posting does not mention.",
    )

    @field_validator("resume_text")
    @classmethod
    def _require_text(cls, value: str) -> str:
        """Reject whitespace-only resumes (the text itself is never echoed)."""

        if not value.strip():
            raise PydanticCustomError("resume_blank", "resume_text must contain text")
        return value


class JobMatchRead(JobRead):
    """One ranked job: every ``JobRead`` field plus how it matches the resume."""

    rank: int
    match_score: float = Field(description="Share of the posting's skills on the resume.")
    blend_score: float = Field(description="0.7 * match_score + 0.3 * score.")
    matched_skills: list[str] = Field(
        description="Posting skills the resume names or implies, in posting order."
    )
    missing_skills: list[str] = Field(
        description="Posting skills the resume lacks, in posting order."
    )
    extra_skills: list[str] | None = Field(
        description="Resume skills the posting does not mention; null unless requested."
    )
    explanation: str


class ResumeMatchResponse(BaseModel):
    """Result of ``POST /jobs/match``."""

    resume_sha256: str = Field(description="SHA-256 of the UTF-8 resume text.")
    resume_skills: list[str] = Field(description="Skills recognized in the resume.")
    implied_skills: dict[str, list[str]] = Field(
        description="Skills the resume demonstrates without naming them, with their sources."
    )
    sort: Literal["match", "blend"]
    total: int = Field(description="Jobs ranked (filters and min_match applied) before limit.")
    jobs: list[JobMatchRead]

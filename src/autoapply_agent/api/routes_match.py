"""``POST /jobs/match``: rank captured jobs against resume text.

The body is read here, not by FastAPI, so that it can be capped while it streams in
(413 above :data:`MAX_MATCH_BODY_BYTES`) and so that validation errors never echo the
resume back. The resume text is used in memory only: it is never written to the
database, and the only log line carries its SHA-256 digest.
"""

from __future__ import annotations

import logging
from email.message import Message
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from autoapply_agent.api.deps import get_session
from autoapply_agent.core.time import utc_now
from autoapply_agent.schemas.jobs import JobRead
from autoapply_agent.schemas.resume_match import (
    JobMatchRead,
    ResumeMatchRequest,
    ResumeMatchResponse,
)
from autoapply_agent.services.job_search import JobSearchFilters, capture_window_start
from autoapply_agent.services.resume_match import (
    MAX_RESUME_CHARS,
    MatchPage,
    MatchSort,
    ResumeProfile,
    rank_jobs,
    render_match_csv,
)

router = APIRouter(prefix="/jobs", tags=["jobs"])
logger = logging.getLogger(__name__)

MAX_MATCH_BODY_BYTES = 1024 * 1024
"""Largest accepted request body; any 50,000-character resume fits, whatever its script."""
CSV_MEDIA_TYPE = "text/csv; charset=utf-8"


def _is_json(content_type: str) -> bool:
    """Whether a ``Content-Type`` header names JSON (``application/json`` or ``*+json``)."""

    message = Message()
    message["content-type"] = content_type
    subtype = message.get_content_subtype()
    return message.get_content_maintype() == "application" and (
        subtype == "json" or subtype.endswith("+json")
    )


def _too_large() -> HTTPException:
    """The 413 error for an oversized body."""

    return HTTPException(
        status_code=status.HTTP_413_CONTENT_TOO_LARGE,
        detail=f"Request body exceeds {MAX_MATCH_BODY_BYTES} bytes; resume_text is limited "
        f"to {MAX_RESUME_CHARS} characters.",
    )


async def read_match_request(request: Request) -> ResumeMatchRequest:
    """Read, cap and validate the JSON body without ever echoing it.

    Args:
        request: Incoming request.

    Returns:
        Validated match request.

    Raises:
        HTTPException: 415 for a non-JSON body, 413 for a body over the cap.
        RequestValidationError: 422 with the usual FastAPI error list, minus inputs.
    """

    content_type = request.headers.get("content-type")
    if content_type is not None and not _is_json(content_type):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Send the match request as JSON (Content-Type: application/json).",
        )
    declared = request.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > MAX_MATCH_BODY_BYTES:
        raise _too_large()
    body = bytearray()
    async for chunk in request.stream():
        body += chunk
        if len(body) > MAX_MATCH_BODY_BYTES:
            raise _too_large()
    if not body.strip():
        raise RequestValidationError(
            [{"type": "missing", "loc": ("body",), "msg": "Field required"}]
        )
    try:
        return ResumeMatchRequest.model_validate_json(bytes(body))
    except ValidationError as exc:
        # Inputs are dropped: the resume (or the whole body) must not come back.
        errors: list[dict[str, Any]] = [
            {**error, "loc": ("body", *error["loc"])}
            for error in exc.errors(include_url=False, include_input=False)
        ]
        raise RequestValidationError(errors) from None


def _filters(payload: ResumeMatchRequest) -> JobSearchFilters:
    """Translate the body filters into the shared ``GET /jobs`` filters."""

    try:
        window_start = capture_window_start(payload.created_after, payload.hours_old, now=utc_now())
    except OverflowError as exc:
        raise RequestValidationError(
            [
                {
                    "type": "datetime_utc_range",
                    "loc": ("body", "created_after"),
                    "msg": "Datetime is outside the supported UTC range",
                }
            ]
        ) from exc
    return JobSearchFilters(
        q=payload.q,
        company=payload.company,
        location=payload.location,
        remote=payload.remote,
        min_score=payload.min_score,
        source_config_id=payload.source_config_id,
        run_id=payload.run_id,
        created_after=window_start,
        dedupe=payload.dedupe,
    )


def _response(
    page: MatchPage, profile: ResumeProfile, *, include_extra_skills: bool
) -> ResumeMatchResponse:
    """Build the JSON response for one ranking."""

    return ResumeMatchResponse(
        resume_sha256=profile.sha256,
        resume_skills=list(profile.skills),
        implied_skills={skill: list(sources) for skill, sources in profile.implied.items()},
        sort=page.sort.value,
        total=page.total,
        jobs=[
            JobMatchRead(
                **JobRead.model_validate(item.job).model_dump(),
                rank=item.rank,
                match_score=item.match.match_score,
                blend_score=item.blend_score,
                matched_skills=list(item.match.matched),
                missing_skills=list(item.match.missing),
                extra_skills=list(item.match.extra) if include_extra_skills else None,
                explanation=item.explanation,
            )
            for item in page.items
        ],
    )


@router.post(
    "/match",
    response_model=ResumeMatchResponse,
    summary="Rank captured jobs against resume text",
    responses={
        200: {
            "description": "Ranked jobs (JSON), or a spreadsheet-safe CSV with format=csv.",
            "content": {"text/csv": {}},
        },
        413: {"description": f"Request body larger than {MAX_MATCH_BODY_BYTES} bytes."},
        415: {"description": "The body is not JSON."},
    },
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {"application/json": {"schema": ResumeMatchRequest.model_json_schema()}},
        }
    },
)
async def match_jobs(
    response: Response,
    payload: Annotated[ResumeMatchRequest, Depends(read_match_request)],
    output_format: Literal["json", "csv"] = Query(
        default="json",
        alias="format",
        description="json, or csv: the match columns followed by the GET /jobs/export columns.",
    ),
    session: AsyncSession = Depends(get_session),
) -> ResumeMatchResponse | Response:
    """Rank the jobs matching the filters by how well they fit the resume.

    Skills are extracted deterministically from the resume and from each job's title and
    description with a curated alias-aware lexicon; ``match_score`` is the share of the
    posting's skills found on the resume. The number of ranked jobs before ``limit`` is
    also returned in the ``X-Total-Count`` header.

    Args:
        response: Outgoing response (receives ``X-Total-Count``).
        payload: Validated body.
        output_format: ``json`` or ``csv``.
        session: Request-scoped async session (read only).

    Returns:
        Ranked jobs as JSON, or a CSV attachment.
    """

    filters = _filters(payload)
    profile = ResumeProfile.from_text(payload.resume_text)
    page = await rank_jobs(
        session,
        filters,
        profile,
        sort=MatchSort(payload.sort),
        limit=payload.limit,
        min_match=payload.min_match,
    )
    logger.info(
        "jobs_match resume_sha256=%s resume_chars=%d resume_skills=%d ranked=%d returned=%d "
        "sort=%s format=%s",
        profile.sha256,
        profile.characters,
        len(profile.skills),
        page.total,
        len(page.items),
        page.sort.value,
        output_format,
    )
    if output_format == "csv":
        filename = f"job-matches-{utc_now():%Y%m%dT%H%M%SZ}.csv"
        return Response(
            content=render_match_csv(page, include_extra_skills=payload.include_extra_skills),
            media_type=CSV_MEDIA_TYPE,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "X-Total-Count": str(page.total),
            },
        )
    response.headers["X-Total-Count"] = str(page.total)
    return _response(page, profile, include_extra_skills=payload.include_extra_skills)

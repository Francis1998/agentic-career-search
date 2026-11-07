"""Job search, detail, export and Atom feed routes."""

import uuid
from collections.abc import AsyncIterator
from dataclasses import replace
from datetime import datetime, timedelta
from typing import Literal
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from autoapply_agent.api.deps import get_session, get_session_factory, get_settings
from autoapply_agent.core.config import Settings
from autoapply_agent.core.time import utc_now
from autoapply_agent.db.models import Job
from autoapply_agent.schemas.jobs import JobRead
from autoapply_agent.services.job_export import iter_csv, iter_jsonl, render_atom_feed
from autoapply_agent.services.job_search import (
    JobSearchFilters,
    JobSort,
    as_utc,
    iter_jobs,
    search_jobs,
)

router = APIRouter(prefix="/jobs", tags=["jobs"])

ATOM_MEDIA_TYPE = "application/atom+xml; charset=utf-8"
EXPORT_MEDIA_TYPES: dict[str, str] = {"csv": "text/csv", "jsonl": "application/x-ndjson"}


def get_job_search_filters(
    q: str | None = Query(
        default=None,
        max_length=200,
        description="Space-separated terms; each must match title, company or location "
        "(case-insensitive substring).",
    ),
    company: str | None = Query(
        default=None, max_length=256, description="Case-insensitive company substring."
    ),
    location: str | None = Query(
        default=None, max_length=256, description="Case-insensitive location substring."
    ),
    remote: bool | None = Query(
        default=None,
        description="true: location mentions remote, anywhere, work from home, wfh, "
        "telecommute or distributed; false: it does not (or is empty).",
    ),
    min_score: float | None = Query(
        default=None, ge=0.0, le=1.0, description="Minimum deterministic score (inclusive)."
    ),
    source_config_id: int | None = Query(
        default=None, ge=1, description="Only jobs captured from this source config."
    ),
    run_id: str | None = Query(default=None, description="Only jobs captured by this run."),
    created_after: datetime | None = Query(
        default=None,
        description="ISO-8601 instant; only jobs captured at or after it (naive means UTC).",
    ),
    hours_old: int | None = Query(
        default=None,
        ge=1,
        le=8760,
        description="Only jobs captured within the last N hours (like JobSpy hours_old).",
    ),
) -> JobSearchFilters:
    """Parse the filter query parameters shared by list, export and feed.

    Args:
        q: Free-text terms.
        company: Company substring.
        location: Location substring.
        remote: Remote filter.
        min_score: Minimum score.
        source_config_id: Source config filter.
        run_id: Run filter.
        created_after: Capture-time lower bound.
        hours_old: Capture-age upper bound in hours.

    Returns:
        Filters; ``created_after`` and ``hours_old`` combine into the later bound.
    """

    bounds = [as_utc(created_after)] if created_after is not None else []
    if hours_old is not None:
        bounds.append(utc_now() - timedelta(hours=hours_old))
    return JobSearchFilters(
        q=q,
        company=company,
        location=location,
        remote=remote,
        min_score=min_score,
        source_config_id=source_config_id,
        run_id=run_id,
        created_after=max(bounds) if bounds else None,
    )


def get_sorted_job_search_filters(
    filters: JobSearchFilters = Depends(get_job_search_filters),
    sort: JobSort = Query(
        default=JobSort.NEWEST,
        description="newest: most recently captured first; score: highest score first "
        "(ties: newest first).",
    ),
    dedupe: bool = Query(
        default=False,
        description="Collapse repeated captures of the same URL and cross-source mirrors "
        "(same normalized title, company and location); the first capture wins.",
    ),
) -> JobSearchFilters:
    """Add ordering and dedupe options to the shared filters.

    Args:
        filters: Shared filters.
        sort: Result ordering.
        dedupe: Whether to collapse duplicates.

    Returns:
        Filters including sort and dedupe mode.
    """

    return replace(filters, sort=sort, dedupe=dedupe)


@router.get("", response_model=list[JobRead])
async def list_jobs(
    response: Response,
    filters: JobSearchFilters = Depends(get_sorted_job_search_filters),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> list[Job]:
    """Search normalized jobs with JobSpy-style filters and pagination.

    The number of matches before ``limit``/``offset`` is returned in the
    ``X-Total-Count`` header. Without parameters this is the newest 50 jobs.

    Args:
        response: Outgoing response (receives ``X-Total-Count``).
        filters: Parsed filters, sort and dedupe mode.
        limit: Max records to return.
        offset: Number of matches to skip.
        session: Request-scoped async session.

    Returns:
        One page of matching jobs.
    """

    page = await search_jobs(session, filters, limit=limit, offset=offset)
    response.headers["X-Total-Count"] = str(page.total)
    return page.items


@router.get(
    "/export",
    response_class=StreamingResponse,
    responses={
        200: {
            "description": "Streamed CSV (OWASP CSV-injection safe) or JSON Lines attachment.",
            "content": {media_type: {} for media_type in EXPORT_MEDIA_TYPES.values()},
        }
    },
)
async def export_jobs(
    filters: JobSearchFilters = Depends(get_sorted_job_search_filters),
    export_format: Literal["csv", "jsonl"] = Query(
        default="csv", alias="format", description="csv (spreadsheets) or jsonl (one job/line)."
    ),
    limit: int | None = Query(
        default=None, ge=1, le=100_000, description="Optional cap; every match by default."
    ),
    session_factory: async_sessionmaker[AsyncSession] = Depends(get_session_factory),
) -> StreamingResponse:
    """Stream every matching job as a CSV or JSON Lines download.

    Args:
        filters: Parsed filters, sort and dedupe mode.
        export_format: ``csv`` or ``jsonl``.
        limit: Optional maximum number of rows.
        session_factory: Factory for the session that lives as long as the stream.

    Returns:
        Streaming attachment response.
    """

    async def body() -> AsyncIterator[str]:
        async with session_factory() as session:
            jobs = iter_jobs(session, filters, limit=limit)
            chunks = iter_csv(jobs) if export_format == "csv" else iter_jsonl(jobs)
            async for chunk in chunks:
                yield chunk

    filename = f"jobs-{utc_now():%Y%m%dT%H%M%SZ}.{export_format}"
    return StreamingResponse(
        body(),
        media_type=EXPORT_MEDIA_TYPES[export_format],
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/feed.atom",
    response_class=Response,
    responses={200: {"description": "Atom 1.0 feed.", "content": {"application/atom+xml": {}}}},
)
async def jobs_feed(
    request: Request,
    filters: JobSearchFilters = Depends(get_job_search_filters),
    limit: int = Query(default=50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> Response:
    """Publish the newest distinct matching postings as an Atom 1.0 feed.

    The feed is always deduplicated and entry ids derive from each posting's first
    capture, so a feed reader notifies once per posting even when later runs or other
    boards capture it again. The feed id derives from the canonical feed URL.

    Args:
        request: Incoming request (self link and fallback entry links).
        filters: Parsed filters.
        limit: Maximum number of entries.
        session: Request-scoped async session.
        settings: Application settings (feed title).

    Returns:
        ``application/atom+xml`` response.
    """

    page = await search_jobs(session, replace(filters, dedupe=True), limit=limit)
    criteria = sorted(
        (key, value) for key, value in request.query_params.multi_items() if key != "limit"
    )
    summary = ", ".join(f"{key}={value}" for key, value in criteria)
    # The canonical feed URL (installation + filters, without limit) keeps ids global.
    canonical_url = str(request.url.replace(query=urlencode(criteria), fragment=""))

    def fallback_link(job: Job) -> str:
        return str(request.url_for("get_job", job_id=job.id))

    document = render_atom_feed(
        [(job, page.postings[job.id]) for job in page.items],
        feed_id=f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, canonical_url)}",
        title=f"{settings.app_name} jobs" + (f" ({summary})" if summary else ""),
        self_url=str(request.url),
        fallback_link=fallback_link,
        generated_at=utc_now(),
    )
    return Response(content=document, media_type=ATOM_MEDIA_TYPE)


@router.get(
    "/{job_id}",
    response_model=JobRead,
    responses={404: {"description": "Job not found"}},
)
async def get_job(job_id: int, session: AsyncSession = Depends(get_session)) -> Job:
    """Get one job by id.

    Args:
        job_id: Job identifier.
        session: Request-scoped async session.

    Returns:
        Job model.
    """

    job = await session.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job not found")
    return job

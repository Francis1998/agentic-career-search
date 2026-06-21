"""Jobs listing route."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from autoapply_agent.api.deps import get_session
from autoapply_agent.db.models import Job
from autoapply_agent.schemas.jobs import JobRead

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=list[JobRead])
async def list_jobs(
    run_id: str | None = None,
    limit: int = Query(default=50, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
) -> list[Job]:
    """List normalized jobs with optional run filter.

    Args:
        run_id: Optional run identifier filter.
        limit: Max records to return.
        session: Request-scoped async session.

    Returns:
        Job list ordered by newest first.
    """

    query = select(Job).order_by(Job.id.desc()).limit(limit)
    if run_id:
        query = select(Job).where(Job.run_id == run_id).order_by(Job.id.desc()).limit(limit)

    result = await session.scalars(query)
    return list(result)

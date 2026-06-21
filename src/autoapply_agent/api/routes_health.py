"""Health check routes."""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from autoapply_agent.api.deps import get_session

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
async def health_live() -> dict[str, str]:
    """Liveness probe endpoint.

    Returns:
        Basic liveness status payload.
    """

    return {"status": "ok"}


@router.get("/ready")
async def health_ready(session: AsyncSession = Depends(get_session)) -> dict[str, str]:
    """Readiness probe endpoint that verifies DB connectivity.

    Args:
        session: Request-scoped async DB session.

    Returns:
        Readiness status payload.
    """

    await session.execute(text("SELECT 1"))
    return {"status": "ready"}

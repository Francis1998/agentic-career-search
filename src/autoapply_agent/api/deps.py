"""Dependency helpers for API routes."""

from collections.abc import AsyncGenerator

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from autoapply_agent.core.config import Settings
from autoapply_agent.db.session import get_session_from_factory
from autoapply_agent.services.worker import InProcessWorker


def get_settings(request: Request) -> Settings:
    """Get settings from application state.

    Args:
        request: FastAPI request object.

    Returns:
        Application settings object.
    """

    return request.app.state.settings


def get_session_factory(request: Request) -> async_sessionmaker[AsyncSession]:
    """Get async session factory from application state.

    Args:
        request: FastAPI request object.

    Returns:
        SQLAlchemy async session factory.
    """

    return request.app.state.session_factory


async def get_session(
    session_factory: async_sessionmaker[AsyncSession] = Depends(get_session_factory),
) -> AsyncGenerator[AsyncSession, None]:
    """Yield an async session for request scope.

    Args:
        session_factory: Injected session factory.

    Yields:
        Request-scoped async session.
    """

    async for session in get_session_from_factory(session_factory):
        yield session


def get_worker(request: Request) -> InProcessWorker:
    """Get worker instance from app state.

    Args:
        request: FastAPI request object.

    Returns:
        In-process worker.
    """

    return request.app.state.worker

"""Async database engine and session helpers."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def create_engine(database_url: str) -> AsyncEngine:
    """Create an async SQLAlchemy engine.

    Args:
        database_url: SQLAlchemy async database URL.

    Returns:
        Configured async engine.
    """

    return create_async_engine(database_url, future=True)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create async session factory for DB operations.

    Args:
        engine: Async SQLAlchemy engine.

    Returns:
        Async sessionmaker instance.
    """

    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_session_from_factory(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    """Yield an async DB session.

    Args:
        session_factory: Session factory from app state.

    Yields:
        Active async session.
    """

    async with session_factory() as session:
        yield session

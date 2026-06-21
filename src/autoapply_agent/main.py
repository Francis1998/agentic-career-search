"""FastAPI application factory and lifecycle wiring."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import APIRouter, FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from autoapply_agent.adapters.greenhouse import GreenhouseAdapter
from autoapply_agent.adapters.lever import LeverAdapter
from autoapply_agent.api.routes_health import router as health_router
from autoapply_agent.api.routes_jobs import router as jobs_router
from autoapply_agent.api.routes_runs import router as runs_router
from autoapply_agent.api.routes_source_configs import router as source_configs_router
from autoapply_agent.core.config import Settings
from autoapply_agent.core.config import settings as default_settings
from autoapply_agent.db.base import Base
from autoapply_agent.db.models import SourceType
from autoapply_agent.db.session import create_engine, create_session_factory
from autoapply_agent.services.planning import DeterministicPlanningService
from autoapply_agent.services.scoring import DeterministicScoringService
from autoapply_agent.services.worker import InProcessWorker


def _create_api_router() -> APIRouter:
    """Create aggregate API router.

    Returns:
        Configured API router.
    """

    router = APIRouter()
    router.include_router(health_router)
    router.include_router(source_configs_router)
    router.include_router(runs_router)
    router.include_router(jobs_router)
    return router


def create_app(custom_settings: Settings | None = None) -> FastAPI:
    """Create FastAPI application instance.

    Args:
        custom_settings: Optional settings override for tests.

    Returns:
        FastAPI app instance.
    """

    active_settings = custom_settings or default_settings

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> Any:
        engine = create_engine(active_settings.database_url)
        session_factory: async_sessionmaker[AsyncSession] = create_session_factory(engine)

        app.state.settings = active_settings
        app.state.engine = engine
        app.state.session_factory = session_factory

        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        worker = InProcessWorker(
            session_factory=session_factory,
            adapters={
                SourceType.GREENHOUSE: GreenhouseAdapter(active_settings.http_user_agent),
                SourceType.LEVER: LeverAdapter(active_settings.http_user_agent),
            },
            scoring_service=DeterministicScoringService(),
            planning_service=DeterministicPlanningService(),
            poll_interval_seconds=active_settings.worker_poll_interval_seconds,
            default_timeout_seconds=active_settings.http_timeout_seconds,
            max_jobs_per_source=active_settings.max_jobs_per_source,
        )
        app.state.worker = worker

        if active_settings.enable_worker:
            await worker.start()

        try:
            yield
        finally:
            await worker.stop()
            await engine.dispose()

    app = FastAPI(title=active_settings.app_name, version="0.1.0", lifespan=lifespan)
    app.include_router(_create_api_router())
    return app


app = create_app()

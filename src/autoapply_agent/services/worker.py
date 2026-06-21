"""In-process async worker for queued run processing."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Mapping

from sqlalchemy import Select, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from autoapply_agent.adapters.base import CareerSourceAdapter, SourceAdapterError
from autoapply_agent.core.time import utc_now
from autoapply_agent.db.models import Job, Run, RunStatus, SourceConfig, SourceType
from autoapply_agent.services.events import append_run_event
from autoapply_agent.services.planning import DeterministicPlanningService
from autoapply_agent.services.scoring import DeterministicScoringService

logger = logging.getLogger(__name__)


class InProcessWorker:
    """Poll queued runs and process them asynchronously."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        adapters: Mapping[SourceType, CareerSourceAdapter],
        scoring_service: DeterministicScoringService,
        planning_service: DeterministicPlanningService,
        poll_interval_seconds: float,
        default_timeout_seconds: float,
        max_jobs_per_source: int,
    ) -> None:
        """Initialize worker dependencies.

        Args:
            session_factory: Async DB session factory.
            adapters: Source adapters by source type.
            scoring_service: Deterministic score service.
            planning_service: Deterministic planning service.
            poll_interval_seconds: Queue polling interval.
            default_timeout_seconds: Default adapter timeout.
            max_jobs_per_source: Per source job cap.
        """

        self._session_factory = session_factory
        self._adapters = adapters
        self._scoring_service = scoring_service
        self._planning_service = planning_service
        self._poll_interval_seconds = poll_interval_seconds
        self._default_timeout_seconds = default_timeout_seconds
        self._max_jobs_per_source = max_jobs_per_source
        self._stop_event = asyncio.Event()
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        """Start worker polling task if not already running."""

        if self._task is not None and not self._task.done():
            return
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run_loop(), name="autoapply-worker")

    async def stop(self) -> None:
        """Stop worker polling task and await completion."""

        self._stop_event.set()
        if self._task is not None:
            await self._task
        self._task = None

    async def _run_loop(self) -> None:
        """Continuously poll and process queued runs."""

        while not self._stop_event.is_set():
            try:
                processed = await self._process_one_queued_run()
                if not processed:
                    await asyncio.wait_for(
                        self._stop_event.wait(),
                        timeout=self._poll_interval_seconds,
                    )
            except TimeoutError:
                continue
            except Exception:
                logger.exception("worker loop iteration failed")
                await asyncio.sleep(self._poll_interval_seconds)

    async def _process_one_queued_run(self) -> bool:
        """Claim and process one queued run.

        Returns:
            True when a run was processed, else False.
        """

        async with self._session_factory() as session:
            claimed_run_id = await self._claim_next_queued_run(session)
            if claimed_run_id is None:
                return False

            await append_run_event(
                session,
                claimed_run_id,
                "run.started",
                "Run moved to running state",
            )
            await session.commit()

        await self._execute_run(claimed_run_id)
        return True

    async def _execute_run(self, run_id: str) -> None:
        """Execute run across configured sources.

        Args:
            run_id: Run identifier.
        """

        try:
            async with self._session_factory() as session:
                run = await self._load_run_or_raise(session, run_id)
                sources = await self._resolve_sources(session, run)
                if not sources:
                    run.status = RunStatus.COMPLETED.value
                    run.finished_at = utc_now()
                    await append_run_event(
                        session,
                        run.id,
                        "run.no_sources",
                        "No matching enabled source configuration found",
                    )
                    await session.commit()
                    return

                for source_config in sources:
                    cancellation_requested = await self._is_cancel_requested(session, run.id)
                    if cancellation_requested:
                        await self._mark_cancelled(session, run)
                        return

                    await self._process_source(session, run, source_config)

                run.status = RunStatus.COMPLETED.value
                run.finished_at = utc_now()
                await append_run_event(
                    session, run.id, "run.completed", "Run completed successfully"
                )
                await session.commit()
        except Exception as exc:
            logger.exception("run execution failed", extra={"run_id": run_id})
            async with self._session_factory() as session:
                run = await self._load_run_or_raise(session, run_id)
                run.status = RunStatus.FAILED.value
                run.error_message = str(exc)
                run.finished_at = utc_now()
                await append_run_event(session, run.id, "run.failed", f"Run failed: {exc!s}")
                await session.commit()

    async def _process_source(
        self, session: AsyncSession, run: Run, source_config: SourceConfig
    ) -> None:
        """Process one configured source for a run.

        Args:
            session: Active async DB session.
            run: Active run model.
            source_config: Source configuration model.
        """

        adapter = self._adapters.get(SourceType(source_config.source_type))
        if adapter is None:
            await append_run_event(
                session,
                run.id,
                "source.unsupported",
                f"No adapter found for source type {source_config.source_type}",
                payload={"source_config_id": source_config.id},
            )
            await session.commit()
            return

        await append_run_event(
            session,
            run.id,
            "source.started",
            f"Processing source config {source_config.name}",
            payload={
                "source_config_id": source_config.id,
                "source_type": source_config.source_type,
            },
        )
        await session.commit()

        timeout_seconds = source_config.timeout_seconds or self._default_timeout_seconds
        try:
            jobs = await adapter.fetch_jobs(
                base_url=source_config.base_url,
                timeout_seconds=timeout_seconds,
                max_jobs=self._max_jobs_per_source,
            )
        except SourceAdapterError as exc:
            await append_run_event(
                session,
                run.id,
                "source.failed",
                f"Source fetch failed: {exc!s}",
                payload={"source_config_id": source_config.id},
            )
            await session.commit()
            return

        inserted_count = 0
        for job_candidate in jobs:
            if await self._is_cancel_requested(session, run.id):
                await self._mark_cancelled(session, run)
                return

            score = self._scoring_service.score(job_candidate, run.query)
            plan_steps = self._planning_service.plan(job_candidate, run.query)
            session.add(
                Job(
                    run_id=run.id,
                    source_config_id=source_config.id,
                    external_id=job_candidate.external_id,
                    title=job_candidate.title,
                    location=job_candidate.location,
                    company=job_candidate.company,
                    url=job_candidate.url,
                    score=score,
                    plan_steps=plan_steps,
                    raw=job_candidate.raw,
                )
            )
            inserted_count += 1

        await append_run_event(
            session,
            run.id,
            "source.completed",
            f"Processed source {source_config.name}",
            payload={"source_config_id": source_config.id, "jobs_inserted": inserted_count},
        )
        await session.commit()

    async def _mark_cancelled(self, session: AsyncSession, run: Run) -> None:
        """Mark run as cancelled and persist event.

        Args:
            session: Active async DB session.
            run: Run model to update.
        """

        run.status = RunStatus.CANCELLED.value
        run.finished_at = utc_now()
        run.cancel_requested = True
        await append_run_event(session, run.id, "run.cancelled", "Run cancelled by request")
        await session.commit()

    async def _resolve_sources(self, session: AsyncSession, run: Run) -> list[SourceConfig]:
        """Resolve enabled source configs for a run.

        Args:
            session: Active async DB session.
            run: Run model.

        Returns:
            List of source configs to process.
        """

        query = (
            select(SourceConfig)
            .where(SourceConfig.enabled.is_(True))
            .order_by(SourceConfig.id.asc())
        )
        if run.source_config_ids:
            query = query.where(SourceConfig.id.in_(run.source_config_ids))
        result = await session.scalars(query)
        return list(result)

    async def _is_cancel_requested(self, session: AsyncSession, run_id: str) -> bool:
        """Check if cancellation was requested for a run.

        Args:
            session: Active async DB session.
            run_id: Run identifier.

        Returns:
            True if cancellation flag is set.
        """

        run = await self._load_run_or_raise(session, run_id)
        return bool(run.cancel_requested)

    @staticmethod
    async def _load_run_or_raise(session: AsyncSession, run_id: str) -> Run:
        """Load run or raise ValueError if missing.

        Args:
            session: Active async DB session.
            run_id: Run identifier.

        Returns:
            Loaded run model.

        Raises:
            ValueError: If run does not exist.
        """

        run = await session.get(Run, run_id)
        if run is None:
            raise ValueError(f"run not found: {run_id}")
        return run

    @staticmethod
    async def _claim_next_queued_run(session: AsyncSession) -> str | None:
        """Atomically claim the next queued run for processing.

        Args:
            session: Active async DB session.

        Returns:
            Claimed run identifier, or None when no run was claimable.
        """

        next_run_query: Select[tuple[str]] = (
            select(Run.id)
            .where(Run.status == RunStatus.QUEUED.value)
            .order_by(Run.created_at.asc())
            .limit(1)
        )
        run_id = await session.scalar(next_run_query)
        if run_id is None:
            return None

        claim_statement = (
            update(Run)
            .where(
                Run.id == run_id,
                Run.status == RunStatus.QUEUED.value,
            )
            .values(
                status=RunStatus.RUNNING.value,
                started_at=utc_now(),
            )
            .returning(Run.id)
        )
        claimed_run_id = await session.scalar(claim_statement)
        if claimed_run_id is None:
            return None

        return claimed_run_id

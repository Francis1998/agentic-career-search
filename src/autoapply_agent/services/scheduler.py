"""In-process scheduler: queue the runs of due schedules every few seconds.

Started from the app lifespan next to the
:class:`~autoapply_agent.services.worker.InProcessWorker` (``ENABLE_SCHEDULER``,
``SCHEDULER_TICK_SECONDS``). Each tick lists the schedules that are due (or hold a
buffered fire) and hands each one to
:func:`~autoapply_agent.services.schedules.process_due_schedule` in its own
transaction; the conditional claim there keeps several ticks or processes from firing
the same schedule twice. The clock is injectable, so ticks are deterministic in tests.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from autoapply_agent.core.time import utc_now
from autoapply_agent.services.job_search import as_utc
from autoapply_agent.services.schedules import FireOutcome, due_schedule_ids, process_due_schedule

logger = logging.getLogger(__name__)

DEFAULT_BATCH_SIZE = 100


class RunScheduler:
    """Poll for due schedules and queue their runs."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        tick_seconds: float,
        clock: Callable[[], datetime] = utc_now,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ) -> None:
        """Initialize scheduler dependencies.

        Args:
            session_factory: Async DB session factory.
            tick_seconds: Pause between ticks.
            clock: Returns the current instant (injectable for tests and demos).
            batch_size: Maximum schedules handled per tick.
        """

        self._session_factory = session_factory
        self._tick_seconds = tick_seconds
        self._clock = clock
        self._batch_size = batch_size
        self._stop_event = asyncio.Event()
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        """Start the tick loop if it is not already running."""

        if self._task is not None and not self._task.done():
            return
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run_loop(), name="autoapply-scheduler")

    async def stop(self) -> None:
        """Stop the tick loop and wait for the current tick to finish."""

        self._stop_event.set()
        if self._task is not None:
            await self._task
        self._task = None

    async def _run_loop(self) -> None:
        """Tick, then sleep until the next tick or a stop request."""

        while not self._stop_event.is_set():
            try:
                await self.tick()
            except Exception:
                logger.exception("scheduler tick failed")
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self._tick_seconds)
            except TimeoutError:
                continue

    async def tick(self, now: datetime | None = None) -> list[FireOutcome]:
        """Handle every due schedule once.

        Args:
            now: Tick instant; defaults to the injected clock.

        Returns:
            What happened to each schedule that was handled (claims lost to another
            tick are left out).
        """

        instant = as_utc(now if now is not None else self._clock())
        async with self._session_factory() as session:
            schedule_ids = await due_schedule_ids(session, now=instant, limit=self._batch_size)
        outcomes: list[FireOutcome] = []
        for schedule_id in schedule_ids:
            try:
                async with self._session_factory() as session:
                    outcome = await process_due_schedule(session, schedule_id, now=instant)
            except Exception:
                logger.exception("schedule tick failed", extra={"schedule_id": schedule_id})
                continue
            if outcome is None:
                continue
            logger.info(
                "schedule_%s schedule_id=%d run_id=%s",
                outcome.kind.value,
                outcome.schedule_id,
                outcome.run_id or "-",
            )
            outcomes.append(outcome)
        return outcomes

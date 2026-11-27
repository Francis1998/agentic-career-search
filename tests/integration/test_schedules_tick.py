"""Scheduler tick semantics: due, overlap skip / buffer_one, misfires, pause, claims."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from autoapply_agent.db.base import Base
from autoapply_agent.db.models import (
    Run,
    RunEvent,
    RunSchedule,
    RunScheduleEvent,
    RunStatus,
    ScheduleEventKind,
)
from autoapply_agent.db.session import create_engine, create_session_factory
from autoapply_agent.services import schedules as schedule_service
from autoapply_agent.services.job_search import as_utc
from autoapply_agent.services.scheduler import RunScheduler
from autoapply_agent.services.schedules import (
    create_schedule,
    jitter_offset,
    pause_schedule,
    process_due_schedule,
    resume_schedule,
    trigger_schedule,
    upcoming_fires,
)

T0 = datetime(2030, 1, 7, 8, 0, tzinfo=UTC)
HOUR = timedelta(hours=1)
Factory = async_sessionmaker[AsyncSession]


@pytest.fixture()
async def factory(tmp_path: Path) -> AsyncIterator[Factory]:
    """Session factory over a fresh SQLite database with the app schema."""

    engine = create_engine(f"sqlite+aiosqlite:///{tmp_path / 'schedules.db'}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    try:
        yield create_session_factory(engine)
    finally:
        await engine.dispose()


async def _create(factory: Factory, *, now: datetime = T0, **values: Any) -> int:
    """Create an hourly interval schedule anchored at T0 (overridable)."""

    defaults: dict[str, Any] = {
        "name": "hourly",
        "kind": "interval",
        "interval_minutes": 60,
        "cron": None,
        "timezone": "UTC",
        "start_at": T0,
        "overlap_policy": "skip",
        "jitter_seconds": 0,
        "paused": False,
        "pause_note": None,
        "query": "python platform",
        "source_config_ids": [1, 2],
    }
    async with factory() as session:
        schedule = await create_schedule(session, {**defaults, **values}, now=now)
        await session.commit()
        return schedule.id


async def _schedule(factory: Factory, schedule_id: int) -> RunSchedule:
    async with factory() as session:
        schedule = await session.get(RunSchedule, schedule_id)
        assert schedule is not None
        return schedule


async def _history(factory: Factory, schedule_id: int) -> list[RunScheduleEvent]:
    async with factory() as session:
        rows = await session.scalars(
            select(RunScheduleEvent)
            .where(RunScheduleEvent.schedule_id == schedule_id)
            .order_by(RunScheduleEvent.id)
        )
        return list(rows)


async def _runs(factory: Factory) -> list[Run]:
    async with factory() as session:
        return list(await session.scalars(select(Run).order_by(Run.created_at)))


async def _finish(factory: Factory, run_id: str | None) -> None:
    async with factory() as session:
        await session.execute(
            update(Run).where(Run.id == run_id).values(status=RunStatus.COMPLETED.value)
        )
        await session.commit()


def _ticker(factory: Factory) -> RunScheduler:
    return RunScheduler(factory, tick_seconds=60, clock=lambda: T0)


def _next(schedule: RunSchedule) -> datetime | None:
    return as_utc(schedule.next_run_at) if schedule.next_run_at is not None else None


async def test_fires_a_normal_queued_run_when_due_and_plans_the_next_fire(
    factory: Factory,
) -> None:
    schedule_id = await _create(factory)
    ticker = _ticker(factory)

    assert await ticker.tick(T0 - timedelta(seconds=1)) == []
    outcomes = await ticker.tick(T0)
    assert await ticker.tick(T0) == []

    assert [outcome.kind for outcome in outcomes] == [ScheduleEventKind.FIRED]
    [run] = await _runs(factory)
    assert (run.status, run.query, run.source_config_ids) == ("queued", "python platform", [1, 2])
    async with factory() as session:
        created = await session.scalar(select(RunEvent).where(RunEvent.run_id == run.id))
    assert created is not None and created.event_type == "run.created"
    assert created.message == "Run queued by schedule 'hourly' (schedule)"
    assert created.payload == {
        "schedule_id": schedule_id,
        "schedule_name": "hourly",
        "trigger": "schedule",
        "scheduled_for": "2030-01-07T08:00:00Z",
    }
    schedule = await _schedule(factory, schedule_id)
    assert (_next(schedule), schedule.last_run_id) == (T0 + HOUR, run.id)
    assert as_utc(schedule.last_fired_at or T0 - HOUR) == T0
    [event] = await _history(factory, schedule_id)
    assert (event.kind, event.run_id, as_utc(event.scheduled_for or T0 - HOUR)) == (
        "fired",
        run.id,
        T0,
    )


async def test_skip_policy_drops_fires_while_the_last_run_is_active(factory: Factory) -> None:
    schedule_id = await _create(factory)
    ticker = _ticker(factory)
    await ticker.tick(T0)
    [first_run] = await _runs(factory)

    skipped = await ticker.tick(T0 + HOUR)
    await _finish(factory, first_run.id)
    fired = await ticker.tick(T0 + 2 * HOUR)

    assert [outcome.kind for outcome in skipped] == [ScheduleEventKind.SKIPPED_OVERLAP]
    assert skipped[0].run_id is None
    assert f"run {first_run.id} is still queued (overlap_policy=skip)" in skipped[0].reason
    assert [outcome.kind for outcome in fired] == [ScheduleEventKind.FIRED]
    assert len(await _runs(factory)) == 2
    assert _next(await _schedule(factory, schedule_id)) == T0 + 3 * HOUR
    kinds = [event.kind for event in await _history(factory, schedule_id)]
    assert kinds == ["fired", "skipped_overlap", "fired"]


async def test_buffer_one_keeps_one_fire_and_starts_it_when_the_run_finishes(
    factory: Factory,
) -> None:
    schedule_id = await _create(factory, overlap_policy="buffer_one")
    ticker = _ticker(factory)
    await ticker.tick(T0)
    [first_run] = await _runs(factory)

    buffered = await ticker.tick(T0 + HOUR)
    skipped = await ticker.tick(T0 + 2 * HOUR)
    still_waiting = await ticker.tick(T0 + 2 * HOUR + timedelta(minutes=5))
    await _finish(factory, first_run.id)
    started = await ticker.tick(T0 + 2 * HOUR + timedelta(minutes=10))

    assert [outcome.kind for outcome in buffered] == [ScheduleEventKind.BUFFERED]
    assert "a fire is already buffered" in skipped[0].reason
    assert still_waiting == []
    assert [outcome.kind for outcome in started] == [ScheduleEventKind.FIRED]
    schedule = await _schedule(factory, schedule_id)
    assert schedule.buffered_at is None
    assert schedule.last_run_id == started[0].run_id
    assert _next(schedule) == T0 + 3 * HOUR
    history = await _history(factory, schedule_id)
    assert [event.kind for event in history] == ["fired", "buffered", "skipped_overlap", "fired"]
    assert as_utc(history[-1].scheduled_for or T0) == T0 + HOUR
    async with factory() as session:
        created = await session.scalar(select(RunEvent).where(RunEvent.run_id == started[0].run_id))
    assert created is not None and created.payload is not None
    assert created.payload["trigger"] == "buffered"


async def test_missed_fires_after_downtime_coalesce_into_one_run(factory: Factory) -> None:
    schedule_id = await _create(factory)
    ticker = _ticker(factory)
    await ticker.tick(T0)
    await _finish(factory, (await _runs(factory))[0].id)

    back_online = T0 + 5 * HOUR + timedelta(minutes=30)
    outcomes = await ticker.tick(back_online)
    again = await ticker.tick(back_online)

    assert [outcome.kind for outcome in outcomes] == [ScheduleEventKind.COALESCED_MISFIRE]
    assert again == []
    assert len(await _runs(factory)) == 2
    assert _next(await _schedule(factory, schedule_id)) == T0 + 6 * HOUR
    event = (await _history(factory, schedule_id))[-1]
    assert event.reason == "coalesced 5 missed fires into one run"
    assert event.details is not None
    assert event.details["missed_fires"] == 5
    assert event.details["latest_scheduled_for"] == "2030-01-07T13:00:00Z"
    assert event.details["late_seconds"] == 4 * 3600 + 30 * 60


async def test_paused_schedule_never_fires_and_resume_does_not_catch_up(
    factory: Factory,
) -> None:
    schedule_id = await _create(factory)
    ticker = _ticker(factory)
    async with factory() as session:
        schedule = await session.get(RunSchedule, schedule_id)
        assert schedule is not None
        await pause_schedule(session, schedule, note="board is down", now=T0 - HOUR)
        await session.commit()

    while_paused = await ticker.tick(T0 + 3 * HOUR)
    async with factory() as session:
        schedule = await session.get(RunSchedule, schedule_id)
        assert schedule is not None
        await resume_schedule(session, schedule, note=None, now=T0 + 3 * HOUR + timedelta(1, 60))
        await session.commit()
    resumed = await _schedule(factory, schedule_id)
    fired = await ticker.tick(_next(resumed) or T0)

    assert while_paused == []
    assert (resumed.paused, resumed.pause_note) == (False, None)
    assert _next(resumed) == T0 + 28 * HOUR
    assert [outcome.kind for outcome in fired] == [ScheduleEventKind.FIRED]
    history = await _history(factory, schedule_id)
    assert [(event.kind, event.reason) for event in history] == [
        ("paused", "board is down"),
        ("resumed", None),
        ("fired", "queued a run"),
    ]


async def test_trigger_honours_the_overlap_policy_and_keeps_the_cadence(
    factory: Factory,
) -> None:
    schedule_id = await _create(factory)
    async with factory() as session:
        schedule = await session.get(RunSchedule, schedule_id)
        assert schedule is not None
        await pause_schedule(session, schedule, note=None, now=T0 - HOUR)
        triggered = await trigger_schedule(session, schedule, now=T0 - HOUR)
        skipped = await trigger_schedule(session, schedule, now=T0 - HOUR)

    assert triggered.kind is ScheduleEventKind.TRIGGERED and triggered.run_id is not None
    assert skipped.kind is ScheduleEventKind.SKIPPED_OVERLAP and skipped.run_id is None
    assert skipped.reason.startswith("manual trigger skipped: run ")
    schedule = await _schedule(factory, schedule_id)
    assert (schedule.paused, schedule.last_run_id) == (True, triggered.run_id)
    assert len(await _runs(factory)) == 1


async def test_two_schedulers_never_fire_the_same_schedule_twice(
    factory: Factory, tmp_path: Path
) -> None:
    schedule_id = await _create(factory)
    other_engine = create_engine(f"sqlite+aiosqlite:///{tmp_path / 'schedules.db'}")
    try:
        first = _ticker(factory)
        second = RunScheduler(create_session_factory(other_engine), tick_seconds=60)
        outcomes = await asyncio.gather(first.tick(T0), second.tick(T0))
    finally:
        await other_engine.dispose()

    assert sum(len(batch) for batch in outcomes) == 1
    assert len(await _runs(factory)) == 1
    assert [event.kind for event in await _history(factory, schedule_id)] == ["fired"]


async def test_a_decision_based_on_a_stale_read_is_rolled_back(factory: Factory) -> None:
    schedule_id = await _create(factory)
    async with factory() as stale_session:
        stale = await stale_session.get(RunSchedule, schedule_id)
        assert stale is not None
        async with factory() as other:
            assert await process_due_schedule(other, schedule_id, now=T0) is not None
        outcome = await schedule_service._fire_due(stale_session, stale, T0)

    assert outcome is None
    assert len(await _runs(factory)) == 1
    assert len(await _history(factory, schedule_id)) == 1


async def test_cron_fires_on_the_local_wall_clock_across_spring_forward(
    factory: Factory,
) -> None:
    friday = datetime(2027, 3, 12, tzinfo=UTC)
    schedule_id = await _create(
        factory,
        now=friday,
        kind="cron",
        interval_minutes=None,
        cron="30 8 * * 1-5",
        timezone="America/Los_Angeles",
        start_at=friday,
    )
    planned = _next(await _schedule(factory, schedule_id))

    await RunScheduler(factory, tick_seconds=60).tick(planned)

    assert planned == datetime(2027, 3, 12, 16, 30, tzinfo=UTC)
    # Monday after the switch to PDT: still 08:30 local, one hour earlier in UTC.
    assert _next(await _schedule(factory, schedule_id)) == datetime(2027, 3, 15, 15, 30, tzinfo=UTC)


async def test_jitter_is_deterministic_bounded_and_previewed(factory: Factory) -> None:
    schedule_id = await _create(factory, jitter_seconds=600)
    schedule = await _schedule(factory, schedule_id)
    offset = jitter_offset(schedule_id, T0, 600)
    planned = _next(schedule)

    fires = upcoming_fires(schedule, 5)
    early = await _ticker(factory).tick(T0 + offset - timedelta(microseconds=1))
    fired = await _ticker(factory).tick(T0 + offset)

    assert planned == T0 + offset
    assert timedelta(0) <= offset <= timedelta(seconds=600)
    assert offset == jitter_offset(schedule_id, T0, 600)
    assert [fire - (T0 + index * HOUR) for index, fire in enumerate(fires)] == [
        jitter_offset(schedule_id, T0 + index * HOUR, 600) for index in range(5)
    ]
    assert early == [] or offset == timedelta(0)
    assert [outcome.kind for outcome in fired] == [ScheduleEventKind.FIRED]
    assert _next(await _schedule(factory, schedule_id)) == fires[1]


async def test_interval_schedules_stay_aligned_to_start_at(factory: Factory) -> None:
    schedule_id = await _create(factory, start_at=T0 - timedelta(hours=10, minutes=30))

    assert _next(await _schedule(factory, schedule_id)) == T0 + timedelta(minutes=30)


async def test_one_broken_schedule_does_not_stop_the_others(factory: Factory) -> None:
    broken_id = await _create(factory, name="broken")
    healthy_id = await _create(factory, name="healthy")
    async with factory() as session:
        await session.execute(
            update(RunSchedule).where(RunSchedule.id == broken_id).values(timezone="Mars/Base")
        )
        await session.commit()

    outcomes = await _ticker(factory).tick(T0)

    assert [outcome.schedule_id for outcome in outcomes] == [healthy_id]


async def test_scheduler_loop_ticks_with_the_injected_clock(factory: Factory) -> None:
    await _create(factory)
    scheduler = RunScheduler(factory, tick_seconds=0.01, clock=lambda: T0)

    await scheduler.start()
    try:
        for _ in range(200):
            if await _runs(factory):
                break
            await asyncio.sleep(0.01)
    finally:
        await scheduler.stop()

    assert len(await _runs(factory)) == 1


async def test_a_trigger_buffered_while_paused_starts_when_the_run_finishes(
    factory: Factory,
) -> None:
    schedule_id = await _create(factory, overlap_policy="buffer_one", paused=True)
    async with factory() as session:
        schedule = await session.get(RunSchedule, schedule_id)
        assert schedule is not None
        first = await trigger_schedule(session, schedule, now=T0)
        buffered = await trigger_schedule(session, schedule, now=T0)
    waiting = await _ticker(factory).tick(T0 + HOUR)
    await _finish(factory, first.run_id)

    started = await _ticker(factory).tick(T0 + 2 * HOUR)

    assert (first.kind, buffered.kind, waiting) == (
        ScheduleEventKind.TRIGGERED,
        ScheduleEventKind.BUFFERED,
        [],
    )
    assert [outcome.kind for outcome in started] == [ScheduleEventKind.FIRED]
    schedule = await _schedule(factory, schedule_id)
    assert (schedule.paused, schedule.next_run_at, schedule.buffered_at) == (True, None, None)


async def test_buffers_waiting_on_active_runs_do_not_starve_due_schedules(
    factory: Factory,
) -> None:
    blocked_id = await _create(factory, name="blocked", overlap_policy="buffer_one", paused=True)
    async with factory() as session:
        blocked = await session.get(RunSchedule, blocked_id)
        assert blocked is not None
        await trigger_schedule(session, blocked, now=T0)
        await trigger_schedule(session, blocked, now=T0)
    due_id = await _create(factory, name="due")

    outcomes = await RunScheduler(factory, tick_seconds=60, batch_size=1).tick(T0)

    assert [outcome.schedule_id for outcome in outcomes] == [due_id]

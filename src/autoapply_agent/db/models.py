"""Database models for runs, events, sources, and jobs."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from autoapply_agent.core.time import utc_now
from autoapply_agent.db.base import Base


class SourceType(StrEnum):
    """Supported career page source adapter types."""

    GREENHOUSE = "greenhouse"
    LEVER = "lever"
    JSONLD = "jsonld"
    ASHBY = "ashby"
    WORKABLE = "workable"
    RECRUITEE = "recruitee"


class RunStatus(StrEnum):
    """Run lifecycle states."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCEL_REQUESTED = "cancel_requested"
    CANCELLED = "cancelled"


class SourceConfig(Base):
    """Configured source endpoints for job scraping."""

    __tablename__ = "source_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    source_type: Mapped[str] = mapped_column(String(24), nullable=False)
    base_url: Mapped[str] = mapped_column(String(512), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    timeout_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )


class Run(Base):
    """Queued or executing run request."""

    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default=RunStatus.QUEUED.value)
    query: Mapped[str | None] = mapped_column(String(256), nullable=True)
    source_config_ids: Mapped[list[int] | None] = mapped_column(JSON, nullable=True)
    cancel_requested: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RunEvent(Base):
    """Persisted ordered event stream for run observability."""

    __tablename__ = "run_events"
    __table_args__ = (UniqueConstraint("run_id", "sequence", name="uq_run_events_run_sequence"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("runs.id"), nullable=False, index=True
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    message: Mapped[str] = mapped_column(String(512), nullable=False)
    payload: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )


class Job(Base):
    """Normalized job listing captured for a run."""

    __tablename__ = "jobs"
    __table_args__ = (UniqueConstraint("run_id", "url", name="uq_jobs_run_url"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("runs.id"), nullable=False, index=True
    )
    source_config_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("source_configs.id"),
        nullable=True,
    )
    external_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    location: Mapped[str | None] = mapped_column(String(256), nullable=True)
    company: Mapped[str | None] = mapped_column(String(256), nullable=True)
    url: Mapped[str] = mapped_column(String(1024), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    plan_steps: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    raw: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

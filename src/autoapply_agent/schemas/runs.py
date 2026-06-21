"""Pydantic schemas for run lifecycle endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from autoapply_agent.db.models import RunStatus


class RunCreate(BaseModel):
    """Payload used to queue a new run."""

    query: str | None = Field(default=None, max_length=256)
    source_config_ids: list[int] | None = None


class RunRead(BaseModel):
    """Run response model."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    status: RunStatus
    query: str | None
    source_config_ids: list[int] | None
    cancel_requested: bool
    error_message: str | None
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class RunEventRead(BaseModel):
    """Run event response model."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    run_id: str
    sequence: int
    event_type: str
    message: str
    payload: dict[str, object] | None
    created_at: datetime

"""Pydantic schemas for jobs listing endpoint."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class JobRead(BaseModel):
    """Job listing response model."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    run_id: str
    source_config_id: int | None
    external_id: str | None
    title: str
    location: str | None
    company: str | None
    url: str
    score: float
    plan_steps: list[str]
    raw: dict[str, object] | None
    created_at: datetime

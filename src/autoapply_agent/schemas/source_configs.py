"""Pydantic schemas for source configuration endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from autoapply_agent.db.models import SourceType


class SourceConfigCreate(BaseModel):
    """Payload to create a source configuration."""

    name: str = Field(min_length=2, max_length=120)
    source_type: SourceType
    base_url: HttpUrl
    enabled: bool = True
    timeout_seconds: float | None = Field(default=None, gt=0)


class SourceConfigUpdate(BaseModel):
    """Payload to update a source configuration."""

    name: str | None = Field(default=None, min_length=2, max_length=120)
    base_url: HttpUrl | None = None
    enabled: bool | None = None
    timeout_seconds: float | None = Field(default=None, gt=0)


class SourceConfigRead(BaseModel):
    """Response model for source configuration records."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    source_type: SourceType
    base_url: str
    enabled: bool
    timeout_seconds: float | None
    created_at: datetime
    updated_at: datetime

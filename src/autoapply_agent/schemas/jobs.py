"""Pydantic schemas for jobs listing endpoint."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


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
    salary_min_annual: int | None = Field(
        default=None,
        description="Lowest captured pay, annualized (hour x2080, day x260, week x52, "
        "month x12); null when the posting states no pay. Full range in raw.compensation.",
    )
    salary_max_annual: int | None = Field(
        default=None, description="Highest captured pay, annualized; null without pay."
    )
    salary_currency: str | None = Field(
        default=None, description="ISO 4217 code of the captured pay; null without pay."
    )
    salary_interval: str | None = Field(
        default=None,
        description="Interval the posting states pay in: hour, day, week, "
        "month or year; null without pay.",
    )
    created_at: datetime

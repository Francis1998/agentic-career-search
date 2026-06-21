"""Source configuration routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from autoapply_agent.api.deps import get_session
from autoapply_agent.db.models import SourceConfig
from autoapply_agent.schemas.source_configs import (
    SourceConfigCreate,
    SourceConfigRead,
    SourceConfigUpdate,
)

router = APIRouter(prefix="/source-configs", tags=["source-configs"])


@router.post("", response_model=SourceConfigRead, status_code=status.HTTP_201_CREATED)
async def create_source_config(
    payload: SourceConfigCreate,
    session: AsyncSession = Depends(get_session),
) -> SourceConfig:
    """Create a source configuration record.

    Args:
        payload: Create payload.
        session: Request-scoped async session.

    Returns:
        Created source config.
    """

    source_config = SourceConfig(
        name=payload.name,
        source_type=payload.source_type.value,
        base_url=str(payload.base_url),
        enabled=payload.enabled,
        timeout_seconds=payload.timeout_seconds,
    )
    session.add(source_config)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="source config with this name already exists",
        ) from exc
    await session.refresh(source_config)
    return source_config


@router.get("", response_model=list[SourceConfigRead])
async def list_source_configs(session: AsyncSession = Depends(get_session)) -> list[SourceConfig]:
    """List source configs.

    Args:
        session: Request-scoped async session.

    Returns:
        Source config list.
    """

    result = await session.scalars(select(SourceConfig).order_by(SourceConfig.id.asc()))
    return list(result)


@router.get("/{source_config_id}", response_model=SourceConfigRead)
async def get_source_config(
    source_config_id: int,
    session: AsyncSession = Depends(get_session),
) -> SourceConfig:
    """Get source config by id.

    Args:
        source_config_id: Source config identifier.
        session: Request-scoped async session.

    Returns:
        Source config model.
    """

    source_config = await session.get(SourceConfig, source_config_id)
    if source_config is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="source config not found")
    return source_config


@router.patch("/{source_config_id}", response_model=SourceConfigRead)
async def update_source_config(
    source_config_id: int,
    payload: SourceConfigUpdate,
    session: AsyncSession = Depends(get_session),
) -> SourceConfig:
    """Patch source config attributes.

    Args:
        source_config_id: Source config identifier.
        payload: Update payload.
        session: Request-scoped async session.

    Returns:
        Updated source config model.
    """

    source_config = await session.get(SourceConfig, source_config_id)
    if source_config is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="source config not found")

    if payload.name is not None:
        source_config.name = payload.name
    if payload.base_url is not None:
        source_config.base_url = str(payload.base_url)
    if payload.enabled is not None:
        source_config.enabled = payload.enabled
    if payload.timeout_seconds is not None:
        source_config.timeout_seconds = payload.timeout_seconds

    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="source config with this name already exists",
        ) from exc

    await session.refresh(source_config)
    return source_config

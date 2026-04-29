from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from src.database import get_db
from src.models.inventory_position import InventoryPosition
from src.models.production_schedule import ProductionSchedule
from src.schemas.inventory import (
    InventoryPositionCreate, InventoryPositionResponse,
    ProductionScheduleCreate, ProductionScheduleResponse,
)

router = APIRouter(prefix="/api/v1", tags=["inventory"])


# ── Inventory Positions ────────────────────────────────────────────────────────

@router.post("/inventory", response_model=InventoryPositionResponse, status_code=201)
async def create_inventory_position(
    payload: InventoryPositionCreate,
    db: AsyncSession = Depends(get_db),
) -> InventoryPositionResponse:
    position = InventoryPosition(
        **payload.model_dump(),
        last_updated_at=datetime.now(timezone.utc),
    )
    db.add(position)
    await db.flush()
    return InventoryPositionResponse.model_validate(position)


@router.get("/inventory", response_model=list[InventoryPositionResponse])
async def list_inventory(
    db: AsyncSession = Depends(get_db),
) -> list[InventoryPositionResponse]:
    result = await db.execute(select(InventoryPosition))
    return [InventoryPositionResponse.model_validate(p) for p in result.scalars().all()]


@router.get("/inventory/{sku_id}", response_model=InventoryPositionResponse)
async def get_inventory_by_sku(
    sku_id: str,
    db: AsyncSession = Depends(get_db),
) -> InventoryPositionResponse:
    result = await db.execute(
        select(InventoryPosition)
        .where(InventoryPosition.sku_id == sku_id)
        .order_by(InventoryPosition.last_updated_at.desc())
    )
    position = result.scalars().first()
    if not position:
        raise HTTPException(status_code=404, detail="Inventory position not found")
    return InventoryPositionResponse.model_validate(position)


# ── Production Schedules ───────────────────────────────────────────────────────

@router.post("/production-schedules", response_model=ProductionScheduleResponse, status_code=201)
async def create_production_schedule(
    payload: ProductionScheduleCreate,
    db: AsyncSession = Depends(get_db),
) -> ProductionScheduleResponse:
    schedule = ProductionSchedule(
        **payload.model_dump(),
        last_updated_at=datetime.now(timezone.utc),
    )
    db.add(schedule)
    await db.flush()
    return ProductionScheduleResponse.model_validate(schedule)


@router.get("/production-schedules", response_model=list[ProductionScheduleResponse])
async def list_production_schedules(
    db: AsyncSession = Depends(get_db),
) -> list[ProductionScheduleResponse]:
    result = await db.execute(
        select(ProductionSchedule).order_by(ProductionSchedule.run_date.asc())
    )
    return [ProductionScheduleResponse.model_validate(s) for s in result.scalars().all()]


@router.get("/production-schedules/{sku_id}", response_model=list[ProductionScheduleResponse])
async def get_schedules_by_sku(
    sku_id: str,
    db: AsyncSession = Depends(get_db),
) -> list[ProductionScheduleResponse]:
    result = await db.execute(
        select(ProductionSchedule)
        .where(ProductionSchedule.sku_id == sku_id)
        .order_by(ProductionSchedule.run_date.asc())
    )
    schedules = result.scalars().all()
    if not schedules:
        raise HTTPException(status_code=404, detail="No schedules found for SKU")
    return [ProductionScheduleResponse.model_validate(s) for s in schedules]

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class InventoryPositionCreate(BaseModel):
    sku_id: str = Field(..., example="SKU-9921")
    warehouse_id: Optional[str] = None
    on_hand_qty: int = Field(..., ge=0)
    safety_stock_qty: int = Field(..., ge=0)
    days_of_cover: float = Field(..., ge=0.0)
    in_transit_qty: int = Field(default=0, ge=0)


class InventoryPositionResponse(BaseModel):
    position_id: str
    sku_id: str
    warehouse_id: Optional[str] = None
    on_hand_qty: int
    safety_stock_qty: int
    days_of_cover: float
    in_transit_qty: int
    snapshot_at: datetime
    last_updated_at: datetime

    model_config = {"from_attributes": True}


class ProductionScheduleCreate(BaseModel):
    production_line: str = Field(..., example="Line-B")
    sku_id: str = Field(..., example="SKU-9921")
    run_date: datetime
    qty_required: int = Field(..., ge=0)
    hard_deadline: Optional[datetime] = None
    shutdown_cost_per_day: float = Field(default=0.0, ge=0.0)
    priority: str = Field(default="normal", example="critical")


class ProductionScheduleResponse(BaseModel):
    schedule_id: str
    production_line: str
    sku_id: str
    run_date: datetime
    qty_required: int
    hard_deadline: Optional[datetime] = None
    shutdown_cost_per_day: float
    priority: str
    last_updated_at: datetime

    model_config = {"from_attributes": True}
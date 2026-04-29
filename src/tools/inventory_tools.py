from langchain_core.tools import tool
from sqlalchemy import select
from src.database import get_sync_db
from src.models.inventory_position import InventoryPosition
from src.models.production_schedule import ProductionSchedule


@tool
def query_inventory_position(sku_id: str) -> dict:
    """
    Query the current inventory position for a given SKU.
    Returns on_hand_qty, safety_stock_qty, days_of_cover, in_transit_qty,
    and last_updated_at. Returns an empty dict if the SKU is not found.
    """
    db = get_sync_db()
    try:
        result = db.execute(
            select(InventoryPosition)
            .where(InventoryPosition.sku_id == sku_id)
            .order_by(InventoryPosition.last_updated_at.desc())
        )
        pos = result.scalars().first()
        if not pos:
            return {}
        return {
            "sku_id": pos.sku_id,
            "warehouse_id": pos.warehouse_id,
            "on_hand_qty": pos.on_hand_qty,
            "safety_stock_qty": pos.safety_stock_qty,
            "days_of_cover": pos.days_of_cover,
            "in_transit_qty": pos.in_transit_qty,
            "last_updated_at": pos.last_updated_at.isoformat(),
        }
    finally:
        db.close()


@tool
def query_production_schedule(sku_id: str) -> dict:
    """
    Query the next upcoming production schedule entry for a given SKU.
    Returns production_line, run_date, qty_required, hard_deadline,
    shutdown_cost_per_day, and priority. Returns an empty dict if not found.
    """
    db = get_sync_db()
    try:
        result = db.execute(
            select(ProductionSchedule)
            .where(ProductionSchedule.sku_id == sku_id)
            .order_by(ProductionSchedule.run_date.asc())
        )
        sched = result.scalars().first()
        if not sched:
            return {}
        return {
            "schedule_id": sched.schedule_id,
            "production_line": sched.production_line,
            "sku_id": sched.sku_id,
            "run_date": sched.run_date.isoformat(),
            "qty_required": sched.qty_required,
            "hard_deadline": (
                sched.hard_deadline.isoformat() if sched.hard_deadline else None
            ),
            "shutdown_cost_per_day": sched.shutdown_cost_per_day,
            "priority": sched.priority,
        }
    finally:
        db.close()


INVENTORY_TOOLS = [query_inventory_position, query_production_schedule]

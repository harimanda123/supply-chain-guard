from sqlalchemy import String, DateTime, Float, Integer
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone
from src.database import Base
import uuid


class InventoryPosition(Base):
    __tablename__ = "inventory_positions"

    position_id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    sku_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    warehouse_id: Mapped[str] = mapped_column(String, nullable=True)
    on_hand_qty: Mapped[int] = mapped_column(Integer, default=0)
    safety_stock_qty: Mapped[int] = mapped_column(Integer, default=0)
    days_of_cover: Mapped[float] = mapped_column(Float, default=0.0)
    in_transit_qty: Mapped[int] = mapped_column(Integer, default=0)
    snapshot_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    last_updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
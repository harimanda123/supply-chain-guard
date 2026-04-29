from sqlalchemy import String, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone
from src.database import Base
import uuid


class ShipmentStatus(Base):
    __tablename__ = "shipment_status"

    status_id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    shipment_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    carrier_ref: Mapped[str] = mapped_column(String, nullable=True)
    mode: Mapped[str] = mapped_column(String, nullable=True)
    current_coords: Mapped[dict] = mapped_column(JSON, nullable=True)
    current_port: Mapped[str] = mapped_column(String, nullable=True)
    sku_manifest: Mapped[dict] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String, default="in_transit")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
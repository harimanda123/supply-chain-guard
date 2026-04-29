from sqlalchemy import String, DateTime, JSON, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone
from src.database import Base
import uuid
import enum


class EventType(str, enum.Enum):
    port_strike = "port_strike"
    vessel_delay = "vessel_delay"
    weather = "weather"
    customs_hold = "customs_hold"


class Severity(str, enum.Enum):
    critical = "critical"
    high = "high"
    medium = "medium"


class DisruptionEvent(Base):
    __tablename__ = "disruption_events"

    event_id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    source_system: Mapped[str] = mapped_column(String, nullable=False)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    shipment_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    affected_skus: Mapped[dict] = mapped_column(JSON, nullable=False)
    location: Mapped[dict] = mapped_column(JSON, nullable=True)
    original_eta: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    revised_eta: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    severity: Mapped[str] = mapped_column(String, nullable=False)
    raw_payload: Mapped[dict] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String, default="received")
    received_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
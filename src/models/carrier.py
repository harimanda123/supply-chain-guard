from sqlalchemy import String, Float, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone
from src.database import Base
import uuid


class Carrier(Base):
    __tablename__ = "carriers"

    carrier_id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    carrier_name: Mapped[str] = mapped_column(String, nullable=False)
    mode: Mapped[str] = mapped_column(String, nullable=False)
    origin_port: Mapped[str] = mapped_column(String, nullable=True)
    dest_port: Mapped[str] = mapped_column(String, nullable=True)
    transit_days: Mapped[int] = mapped_column(Integer, default=0)
    rate_per_unit: Mapped[float] = mapped_column(Float, default=0.0)
    availability_date: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    reliability_score: Mapped[float] = mapped_column(Float, default=0.0)
    last_updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
from sqlalchemy import String, DateTime, Integer, Float
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone
from src.database import Base
import uuid


class ProductionSchedule(Base):
    __tablename__ = "production_schedules"

    schedule_id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    production_line: Mapped[str] = mapped_column(String, nullable=False)
    sku_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    run_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    qty_required: Mapped[int] = mapped_column(Integer, default=0)
    hard_deadline: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    shutdown_cost_per_day: Mapped[float] = mapped_column(Float, default=0.0)
    priority: Mapped[str] = mapped_column(String, default="normal")
    last_updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
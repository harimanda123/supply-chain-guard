from sqlalchemy import String, Float
from sqlalchemy.orm import Mapped, mapped_column
from src.database import Base
import uuid


class FinancialRule(Base):
    __tablename__ = "financial_rules"

    rule_id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    sku_id: Mapped[str] = mapped_column(String, nullable=True, index=True)
    max_expedite_budget: Mapped[float] = mapped_column(Float, default=0.0)
    auto_approve_ceiling: Mapped[float] = mapped_column(Float, default=0.0)
    penalty_per_day: Mapped[float] = mapped_column(Float, default=0.0)
    baseline_freight_cost: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String, default="USD")
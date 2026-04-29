from sqlalchemy import String, Boolean, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone
from src.database import Base
import uuid


class ComplianceRegistry(Base):
    __tablename__ = "compliance_registry"

    entry_id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    carrier_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    is_blacklisted: Mapped[bool] = mapped_column(Boolean, default=False)
    insurance_valid: Mapped[bool] = mapped_column(Boolean, default=True)
    insurance_expiry: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    certifications: Mapped[dict] = mapped_column(JSON, nullable=True)
    last_verified_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
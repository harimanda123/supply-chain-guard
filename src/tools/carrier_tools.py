from langchain_core.tools import tool
from sqlalchemy import select
from typing import Optional
from src.database import get_sync_db
from src.models.carrier import Carrier


@tool
def query_carriers(mode: Optional[str] = None) -> list[dict]:
    """
    Query all available carriers from the carrier catalog.
    Optionally filter by mode: 'air', 'sea', 'road', or 'sea-air'.
    Returns a list of carriers with carrier_id, carrier_name, mode,
    transit_days, rate_per_unit, and reliability_score.
    """
    db = get_sync_db()
    try:
        stmt = select(Carrier)
        if mode:
            stmt = stmt.where(Carrier.mode == mode)
        result = db.execute(stmt)
        carriers = result.scalars().all()
        return [
            {
                "carrier_id": c.carrier_id,
                "carrier_name": c.carrier_name,
                "mode": c.mode,
                "origin_port": c.origin_port,
                "dest_port": c.dest_port,
                "transit_days": c.transit_days,
                "rate_per_unit": c.rate_per_unit,
                "reliability_score": c.reliability_score,
            }
            for c in carriers
        ]
    finally:
        db.close()


@tool
def get_carrier_by_id(carrier_id: str) -> dict:
    """
    Retrieve full details for a specific carrier by carrier_id.
    Returns an empty dict if the carrier is not found.
    """
    db = get_sync_db()
    try:
        result = db.execute(
            select(Carrier).where(Carrier.carrier_id == carrier_id)
        )
        c = result.scalars().first()
        if not c:
            return {}
        return {
            "carrier_id": c.carrier_id,
            "carrier_name": c.carrier_name,
            "mode": c.mode,
            "origin_port": c.origin_port,
            "dest_port": c.dest_port,
            "transit_days": c.transit_days,
            "rate_per_unit": c.rate_per_unit,
            "reliability_score": c.reliability_score,
            "last_updated_at": c.last_updated_at.isoformat(),
        }
    finally:
        db.close()


CARRIER_TOOLS = [query_carriers, get_carrier_by_id]

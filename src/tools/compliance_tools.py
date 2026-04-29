from langchain_core.tools import tool
from sqlalchemy import select
from src.database import get_sync_db
from src.models.compliance_registry import ComplianceRegistry


@tool
def check_carrier_compliance(carrier_id: str) -> dict:
    """
    Check the compliance record for a carrier.
    Returns is_blacklisted, insurance_valid, insurance_expiry, certifications,
    and last_verified_at. Returns a default-safe dict if no record exists
    (treats unknown carriers as requiring manual review).
    """
    db = get_sync_db()
    try:
        result = db.execute(
            select(ComplianceRegistry).where(
                ComplianceRegistry.carrier_id == carrier_id
            )
        )
        entry = result.scalars().first()
        if not entry:
            return {
                "found": False,
                "carrier_id": carrier_id,
                "is_blacklisted": False,
                "insurance_valid": False,
                "insurance_expiry": None,
                "certifications": {},
                "last_verified_at": None,
                "note": "No compliance record found — manual review required",
            }
        return {
            "found": True,
            "carrier_id": carrier_id,
            "is_blacklisted": entry.is_blacklisted,
            "insurance_valid": entry.insurance_valid,
            "insurance_expiry": (
                entry.insurance_expiry.isoformat() if entry.insurance_expiry else None
            ),
            "certifications": entry.certifications or {},
            "last_verified_at": entry.last_verified_at.isoformat(),
        }
    finally:
        db.close()


COMPLIANCE_TOOLS = [check_carrier_compliance]

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from src.database import get_db
from src.models.carrier import Carrier
from src.models.compliance_registry import ComplianceRegistry
from src.schemas.carrier import (
    CarrierCreate, CarrierResponse,
    ComplianceRegistryCreate, ComplianceRegistryResponse,
)

router = APIRouter(prefix="/api/v1", tags=["carriers"])


# ── Carriers ───────────────────────────────────────────────────────────────────

@router.post("/carriers", response_model=CarrierResponse, status_code=201)
async def create_carrier(
    payload: CarrierCreate,
    db: AsyncSession = Depends(get_db),
) -> CarrierResponse:
    carrier = Carrier(**payload.model_dump())
    db.add(carrier)
    await db.flush()
    return CarrierResponse.model_validate(carrier)


@router.get("/carriers", response_model=list[CarrierResponse])
async def list_carriers(
    db: AsyncSession = Depends(get_db),
) -> list[CarrierResponse]:
    result = await db.execute(select(Carrier))
    return [CarrierResponse.model_validate(c) for c in result.scalars().all()]


@router.get("/carriers/{carrier_id}", response_model=CarrierResponse)
async def get_carrier(
    carrier_id: str,
    db: AsyncSession = Depends(get_db),
) -> CarrierResponse:
    result = await db.execute(
        select(Carrier).where(Carrier.carrier_id == carrier_id)
    )
    carrier = result.scalar_one_or_none()
    if not carrier:
        raise HTTPException(status_code=404, detail="Carrier not found")
    return CarrierResponse.model_validate(carrier)


@router.delete("/carriers/{carrier_id}", status_code=204)
async def delete_carrier(
    carrier_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(
        select(Carrier).where(Carrier.carrier_id == carrier_id)
    )
    carrier = result.scalar_one_or_none()
    if not carrier:
        raise HTTPException(status_code=404, detail="Carrier not found")
    await db.delete(carrier)


# ── Compliance Registry ────────────────────────────────────────────────────────

@router.post("/compliance", response_model=ComplianceRegistryResponse, status_code=201)
async def create_compliance_entry(
    payload: ComplianceRegistryCreate,
    db: AsyncSession = Depends(get_db),
) -> ComplianceRegistryResponse:
    entry = ComplianceRegistry(
        **payload.model_dump(),
        last_verified_at=datetime.now(timezone.utc),
    )
    db.add(entry)
    await db.flush()
    return ComplianceRegistryResponse.model_validate(entry)


@router.get("/compliance/{carrier_id}", response_model=ComplianceRegistryResponse)
async def get_compliance(
    carrier_id: str,
    db: AsyncSession = Depends(get_db),
) -> ComplianceRegistryResponse:
    result = await db.execute(
        select(ComplianceRegistry).where(
            ComplianceRegistry.carrier_id == carrier_id
        )
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Compliance entry not found")
    return ComplianceRegistryResponse.model_validate(entry)

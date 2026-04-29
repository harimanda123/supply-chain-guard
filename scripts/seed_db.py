"""
Seed script — populates the database with realistic test data.

Run with:  uv run python -m scripts.seed_db

Seeds:
  - 3 carriers (air, sea-air hybrid, road)
  - compliance records for each carrier
  - inventory position for SKU-9921
  - production schedule for SKU-9921
  - financial rules for SKU-9921 (and a global default)
"""
import asyncio
from datetime import datetime, timezone, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from src.database import AsyncSessionLocal, init_db
from src.models.carrier import Carrier
from src.models.compliance_registry import ComplianceRegistry
from src.models.inventory_position import InventoryPosition
from src.models.production_schedule import ProductionSchedule
from src.models.financial_rule import FinancialRule


async def seed() -> None:
    await init_db()

    async with AsyncSessionLocal() as session:
        await _seed_carriers(session)
        await _seed_inventory(session)
        await _seed_financial_rules(session)
        await session.commit()

    print("Seed complete.")


async def _seed_carriers(session: AsyncSession) -> None:
    carriers = [
        {
            "carrier_name": "DHL Express",
            "mode": "air",
            "origin_port": "CNSHA",
            "dest_port": "USLAX",
            "transit_days": 2,
            "rate_per_unit": 12000.0,
            "reliability_score": 92.0,
            "compliance": {
                "is_blacklisted": False,
                "insurance_valid": True,
                "insurance_expiry": datetime(2027, 6, 30, tzinfo=timezone.utc),
                "certifications": {"IATA": True, "GDP": True},
            },
        },
        {
            "carrier_name": "Flexport Sea-Air",
            "mode": "sea-air",
            "origin_port": "CNSHA",
            "dest_port": "USLAX",
            "transit_days": 5,
            "rate_per_unit": 7500.0,
            "reliability_score": 85.0,
            "compliance": {
                "is_blacklisted": False,
                "insurance_valid": True,
                "insurance_expiry": datetime(2027, 3, 31, tzinfo=timezone.utc),
                "certifications": {"IATA": False, "GDP": True},
            },
        },
        {
            "carrier_name": "DB Schenker Road",
            "mode": "road",
            "origin_port": None,
            "dest_port": None,
            "transit_days": 8,
            "rate_per_unit": 3200.0,
            "reliability_score": 78.0,
            "compliance": {
                "is_blacklisted": False,
                "insurance_valid": True,
                "insurance_expiry": datetime(2026, 12, 31, tzinfo=timezone.utc),
                "certifications": {"GDP": True},
            },
        },
        {
            "carrier_name": "Blacklisted Freight Co",
            "mode": "sea",
            "origin_port": "CNSHA",
            "dest_port": "USLAX",
            "transit_days": 20,
            "rate_per_unit": 800.0,
            "reliability_score": 40.0,
            "compliance": {
                "is_blacklisted": True,
                "insurance_valid": False,
                "insurance_expiry": datetime(2023, 1, 1, tzinfo=timezone.utc),
                "certifications": {},
            },
        },
    ]

    for c_data in carriers:
        comp_data = c_data.pop("compliance")
        carrier = Carrier(**c_data)
        session.add(carrier)
        await session.flush()  # get carrier_id

        compliance = ComplianceRegistry(
            carrier_id=carrier.carrier_id,
            **comp_data,
            last_verified_at=datetime.now(timezone.utc),
        )
        session.add(compliance)

    print(f"  Seeded {len(carriers)} carriers with compliance records.")


async def _seed_inventory(session: AsyncSession) -> None:
    # Inventory position for SKU-9921 — critically low
    inv = InventoryPosition(
        sku_id="SKU-9921",
        warehouse_id="WH-US-WEST",
        on_hand_qty=150,
        safety_stock_qty=200,
        days_of_cover=3.0,   # only 3 days of stock left
        in_transit_qty=500,
        last_updated_at=datetime.now(timezone.utc),
    )
    session.add(inv)

    # Production schedule — hard deadline in 4 days
    hard_deadline = datetime.now(timezone.utc) + timedelta(days=4)
    schedule = ProductionSchedule(
        production_line="Line-B",
        sku_id="SKU-9921",
        run_date=datetime.now(timezone.utc) + timedelta(days=3),
        qty_required=500,
        hard_deadline=hard_deadline,
        shutdown_cost_per_day=50000.0,
        priority="critical",
        last_updated_at=datetime.now(timezone.utc),
    )
    session.add(schedule)

    print("  Seeded inventory position + production schedule for SKU-9921.")


async def _seed_financial_rules(session: AsyncSession) -> None:
    # SKU-specific rule
    sku_rule = FinancialRule(
        sku_id="SKU-9921",
        max_expedite_budget=15000.0,
        auto_approve_ceiling=5000.0,
        penalty_per_day=50000.0,
        baseline_freight_cost=3200.0,
        currency="USD",
    )
    session.add(sku_rule)

    # Global default fallback
    default_rule = FinancialRule(
        sku_id=None,
        max_expedite_budget=10000.0,
        auto_approve_ceiling=3000.0,
        penalty_per_day=25000.0,
        baseline_freight_cost=0.0,
        currency="USD",
    )
    session.add(default_rule)

    print("  Seeded financial rules (SKU-9921 + global default).")


if __name__ == "__main__":
    asyncio.run(seed())

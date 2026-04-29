import asyncio, sys, json
sys.stdout.reconfigure(encoding="utf-8")
from sqlalchemy import select
from src.database import AsyncSessionLocal
from src.models.disruption_event import DisruptionEvent

async def main():
    event_id = "af9ad0c1-dbeb-434d-b155-0f51fe7e7245"
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(DisruptionEvent).where(DisruptionEvent.event_id == event_id)
        )
        ev = result.scalar_one_or_none()
        if not ev:
            print("Event not found")
            return
        raw = ev.raw_payload or {}
        print("Status:", ev.status)
        print("Pipeline error:", raw.get("pipeline_error", "(none)"))
        print("Full raw_payload:", json.dumps(raw, indent=2, default=str))

asyncio.run(main())

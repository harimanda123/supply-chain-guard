import asyncio
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models.disruption_event import DisruptionEvent
from src.models.inventory_position import InventoryPosition
from src.models.production_schedule import ProductionSchedule
from src.models.carrier import Carrier
from src.models.financial_rule import FinancialRule
from src.models.compliance_registry import ComplianceRegistry
from src.schemas.disruption import DisruptionEventCreate, DisruptionEventResponse
from src.schemas.resolution import ResolutionPlan, AgentAuditEntry

router = APIRouter(prefix="/api/v1/events", tags=["disruptions"])

# Staleness threshold from HLD section 5.3
STALENESS_HOURS = 2


async def _run_pipeline(event_id: str) -> None:
    """
    Background task — loads context from DB, runs the LangGraph pipeline,
    and writes the resolution back to the disruption record.
    Imported lazily to avoid circular import at module load time.
    """
    from src.graph.pipeline import pipeline
    from src.database import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        # ── Load disruption event ─────────────────────────────────────────────
        result = await session.execute(
            select(DisruptionEvent).where(DisruptionEvent.event_id == event_id)
        )
        event = result.scalar_one_or_none()
        if not event:
            return

        affected_skus = event.affected_skus  # list of {sku, qty}
        first_sku = affected_skus[0]["sku"] if affected_skus else None

        # ── Compute delay_days ────────────────────────────────────────────────
        delay_days = 0
        if event.original_eta and event.revised_eta:
            delay_days = max(0, (event.revised_eta - event.original_eta).days)

        # ── Load inventory position for first SKU ─────────────────────────────
        inv = None
        stale = False
        if first_sku:
            inv_result = await session.execute(
                select(InventoryPosition)
                .where(InventoryPosition.sku_id == first_sku)
                .order_by(InventoryPosition.last_updated_at.desc())
            )
            inv = inv_result.scalars().first()
            if inv:
                age = datetime.now(timezone.utc) - inv.last_updated_at.replace(
                    tzinfo=timezone.utc
                )
                stale = age > timedelta(hours=STALENESS_HOURS)

        # ── Load production schedule for first SKU ────────────────────────────
        sched = None
        if first_sku:
            sched_result = await session.execute(
                select(ProductionSchedule)
                .where(ProductionSchedule.sku_id == first_sku)
                .order_by(ProductionSchedule.run_date.asc())
            )
            sched = sched_result.scalars().first()

        # ── Load carrier options ──────────────────────────────────────────────
        carriers_result = await session.execute(select(Carrier))
        carriers = carriers_result.scalars().all()
        carrier_options = [
            {
                "carrier_id": c.carrier_id,
                "carrier_name": c.carrier_name,
                "mode": c.mode,
                "transit_days": c.transit_days,
                "rate_per_unit": c.rate_per_unit,
                "reliability_score": c.reliability_score,
            }
            for c in carriers
        ]

        # ── Load financial rule for first SKU (or default) ────────────────────
        fin_rule = None
        if first_sku:
            fin_result = await session.execute(
                select(FinancialRule).where(FinancialRule.sku_id == first_sku)
            )
            fin_rule = fin_result.scalars().first()
        if not fin_rule:
            # Fallback to global default rule (sku_id IS NULL)
            fin_result = await session.execute(
                select(FinancialRule).where(FinancialRule.sku_id.is_(None))
            )
            fin_rule = fin_result.scalars().first()

        # ── Load compliance data for first carrier (if available) ─────────────
        first_carrier_id = carrier_options[0]["carrier_id"] if carrier_options else ""
        comp = None
        if first_carrier_id:
            comp_result = await session.execute(
                select(ComplianceRegistry).where(
                    ComplianceRegistry.carrier_id == first_carrier_id
                )
            )
            comp = comp_result.scalars().first()

        hard_deadline_str = (
            sched.hard_deadline.strftime("%Y-%m-%d")
            if sched and sched.hard_deadline
            else (datetime.now(timezone.utc) + timedelta(days=7)).strftime("%Y-%m-%d")
        )

        # ── Build initial state ───────────────────────────────────────────────
        initial_state = {
            # Disruption
            "event_id": event_id,
            "source_system": event.source_system,
            "shipment_id": event.shipment_id,
            "affected_skus": affected_skus,
            "delay_days": delay_days,
            "severity": event.severity,
            # Inventory
            "on_hand_qty": inv.on_hand_qty if inv else 0,
            "safety_stock_qty": inv.safety_stock_qty if inv else 0,
            "days_of_cover": inv.days_of_cover if inv else 0.0,
            "days_of_buffer": 0,
            "hard_deadline": hard_deadline_str,
            "shutdown_cost_per_day": sched.shutdown_cost_per_day if sched else 0.0,
            "can_wait": False,
            "urgency_level": "medium",
            # Route proposal (empty — agents will fill)
            "proposed_carrier_name": "",
            "proposed_carrier_id": "",
            "proposed_mode": "",
            "proposed_cost": 0.0,
            "proposed_transit_days": 0,
            "carrier_options": carrier_options,
            # Financial
            "max_expedite_budget": fin_rule.max_expedite_budget if fin_rule else 15000.0,
            "penalty_per_day": fin_rule.penalty_per_day if fin_rule else 50000.0,
            "auto_approve_ceiling": fin_rule.auto_approve_ceiling if fin_rule else 5000.0,
            "financially_approved": False,
            "savings_achieved": 0.0,
            "cost_vs_penalty_summary": "",
            # Compliance
            "is_blacklisted": comp.is_blacklisted if comp else False,
            "insurance_valid": comp.insurance_valid if comp else True,
            "insurance_expiry": (
                comp.insurance_expiry.strftime("%Y-%m-%d")
                if comp and comp.insurance_expiry
                else "N/A"
            ),
            "reliability_score": carrier_options[0]["reliability_score"] if carrier_options else 0.0,
            "certifications": comp.certifications if comp else {},
            "compliance_cleared": False,
            "compliance_checks_passed": [],
            "compliance_checks_failed": [],
            # Loop control
            "iteration": 1,
            "max_iterations": 5,
            # Resolution
            "resolution_status": "processing",
            "audit_trail": [],
            "error_message": None,
        }

        # ── Escalate immediately if inventory data is stale ───────────────────
        if stale:
            await session.execute(
                select(DisruptionEvent).where(DisruptionEvent.event_id == event_id)
            )
            event.status = "escalated_stale_data"
            await session.commit()
            return

        # ── Run pipeline ──────────────────────────────────────────────────────
        try:
            final_state = await asyncio.get_event_loop().run_in_executor(
                None, lambda: pipeline.invoke(initial_state)
            )
            event.status = final_state.get("resolution_status", "processing")
        except Exception as exc:  # noqa: BLE001
            event.status = "error"
            event.raw_payload = {
                **(event.raw_payload or {}),
                "pipeline_error": str(exc),
            }

        await session.commit()


@router.post(
    "/disruption",
    response_model=DisruptionEventResponse,
    status_code=202,
    summary="Receive a disruption event webhook from an ERP or TMS",
)
async def receive_disruption(
    payload: DisruptionEventCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> DisruptionEventResponse:
    """
    Validates the incoming disruption payload, persists it, and enqueues
    the autonomous recovery pipeline as a background task.
    Returns 202 Accepted immediately — the pipeline runs asynchronously.
    """
    event = DisruptionEvent(
        source_system=payload.source_system,
        event_type=payload.event_type.value,
        shipment_id=payload.shipment_id,
        affected_skus=[s.model_dump() for s in payload.affected_skus],
        location=payload.location.model_dump() if payload.location else None,
        original_eta=payload.original_eta,
        revised_eta=payload.revised_eta,
        severity=payload.severity.value,
        raw_payload=payload.model_dump(mode="json"),
        status="received",
    )
    db.add(event)
    await db.flush()  # assigns event_id before background task is queued

    background_tasks.add_task(_run_pipeline, event.event_id)

    return DisruptionEventResponse.model_validate(event)


@router.get(
    "/disruption/{event_id}",
    response_model=DisruptionEventResponse,
    summary="Get the current status of a disruption event",
)
async def get_disruption(
    event_id: str,
    db: AsyncSession = Depends(get_db),
) -> DisruptionEventResponse:
    result = await db.execute(
        select(DisruptionEvent).where(DisruptionEvent.event_id == event_id)
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return DisruptionEventResponse.model_validate(event)

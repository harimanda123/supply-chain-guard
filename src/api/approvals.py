from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from src.database import get_db
from src.models.disruption_event import DisruptionEvent
from src.schemas.resolution import (
    ResolutionPlan, ApprovalRequest, ApprovalResponse, AgentAuditEntry,
)
from src import events as event_bus

router = APIRouter(prefix="/api/v1/approvals", tags=["approvals"])

# Resolution status values that indicate an agent run has completed
_RESOLUTION_STATUSES = {"pending_approval", "escalated", "escalated_stale_data"}


@router.get(
    "/pending",
    response_model=list[ResolutionPlan],
    summary="List all events awaiting human approval",
)
async def list_pending(
    db: AsyncSession = Depends(get_db),
) -> list[ResolutionPlan]:
    result = await db.execute(
        select(DisruptionEvent).where(
            DisruptionEvent.status == "pending_approval"
        )
    )
    events = result.scalars().all()
    plans = []
    for ev in events:
        raw = ev.raw_payload or {}
        plans.append(
            ResolutionPlan(
                event_id=ev.event_id,
                recommended_carrier=raw.get("proposed_carrier_name", ""),
                recommended_mode=raw.get("proposed_mode", ""),
                estimated_cost=raw.get("proposed_cost", 0.0),
                estimated_eta_days=raw.get("proposed_transit_days", 0),
                cost_vs_penalty=raw.get("cost_vs_penalty_summary", ""),
                audit_trail=[
                    AgentAuditEntry(**e)
                    for e in raw.get("audit_trail", [])
                ],
                status=ev.status,
                created_at=ev.received_at,
            )
        )
    return plans


@router.get(
    "/{event_id}",
    response_model=ResolutionPlan,
    summary="Get the resolution plan for a specific event",
)
async def get_resolution(
    event_id: str,
    db: AsyncSession = Depends(get_db),
) -> ResolutionPlan:
    result = await db.execute(
        select(DisruptionEvent).where(DisruptionEvent.event_id == event_id)
    )
    ev = result.scalar_one_or_none()
    if not ev:
        raise HTTPException(status_code=404, detail="Event not found")
    if ev.status not in _RESOLUTION_STATUSES:
        raise HTTPException(
            status_code=409,
            detail=f"Event is still processing (status: {ev.status})",
        )
    raw = ev.raw_payload or {}
    return ResolutionPlan(
        event_id=ev.event_id,
        recommended_carrier=raw.get("proposed_carrier_name", ""),
        recommended_mode=raw.get("proposed_mode", ""),
        estimated_cost=raw.get("proposed_cost", 0.0),
        estimated_eta_days=raw.get("proposed_transit_days", 0),
        cost_vs_penalty=raw.get("cost_vs_penalty_summary", ""),
        audit_trail=[
            AgentAuditEntry(**e)
            for e in raw.get("audit_trail", [])
        ],
        status=ev.status,
        created_at=ev.received_at,
    )


@router.post(
    "/{event_id}/approve",
    response_model=ApprovalResponse,
    summary="Human reviewer approves or rejects a resolution plan",
)
async def approve_resolution(
    event_id: str,
    payload: ApprovalRequest,
    db: AsyncSession = Depends(get_db),
) -> ApprovalResponse:
    result = await db.execute(
        select(DisruptionEvent).where(DisruptionEvent.event_id == event_id)
    )
    ev = result.scalar_one_or_none()
    if not ev:
        raise HTTPException(status_code=404, detail="Event not found")
    if ev.status != "pending_approval":
        raise HTTPException(
            status_code=409,
            detail=f"Event is not pending approval (status: {ev.status})",
        )

    ev.status = "approved" if payload.approved else "rejected"
    ev.raw_payload = {
        **(ev.raw_payload or {}),
        "reviewer_note": payload.reviewer_note,
        "reviewed_at": datetime.utcnow().isoformat(),
    }

    # ── TMS writeback on approval ─────────────────────────────────────────────
    booking_ref = ""
    if payload.approved:
        from src.adapters.tms_output import execute_writeback, BookingRequest
        import os

        raw = ev.raw_payload or {}
        booking = BookingRequest(
            event_id=event_id,
            carrier_name=raw.get("proposed_carrier_name", ""),
            carrier_id=raw.get("proposed_carrier_id", ""),
            mode=raw.get("proposed_mode", ""),
            estimated_cost=raw.get("proposed_cost", 0.0),
            transit_days=raw.get("proposed_transit_days", 0),
            shipment_id=ev.shipment_id,
            affected_skus=ev.affected_skus or [],
            hard_deadline=raw.get("hard_deadline", ""),
            reviewer_note=payload.reviewer_note or "",
        )
        target = os.environ.get("TMS_ADAPTER", "log_only")
        confirmation = await execute_writeback(target, booking)
        booking_ref = confirmation.booking_reference
        ev.raw_payload = {
            **ev.raw_payload,
            "booking_reference": booking_ref,
            "booking_status": confirmation.status,
            "booking_confirmed_at": confirmation.confirmed_at,
        }

    message = (
        f"Resolution approved. Booking reference: {booking_ref or 'pending'}."
        if payload.approved
        else "Resolution rejected by reviewer."
    )
    return ApprovalResponse(event_id=event_id, status=ev.status, message=message)


@router.get(
    "/stream",
    summary="SSE stream — all resolution events (use event_id filter for one event)",
    response_class=StreamingResponse,
)
async def stream_all_resolutions() -> StreamingResponse:
    """
    Server-Sent Events stream for all resolution completions.
    Connect once and receive a JSON payload for every event that reaches
    pending_approval, escalated, or error status.
    """
    return StreamingResponse(
        event_bus.subscribe("*"),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get(
    "/stream/{event_id}",
    summary="SSE stream scoped to a single disruption event",
    response_class=StreamingResponse,
)
async def stream_resolution(event_id: str) -> StreamingResponse:
    """
    Server-Sent Events stream for a specific disruption event.
    Emits one payload when the pipeline completes or escalates.
    """
    return StreamingResponse(
        event_bus.subscribe(event_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )

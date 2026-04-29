"""
TMS Output Adapter — pluggable booking writeback layer.

When a human approves a resolution, the engine calls the registered
output adapter for the relevant TMS/carrier system to confirm the booking.

Usage
-----
Register a writeback function for each TMS target:

    from src.adapters.tms_output import register_writeback

    @register_writeback("dhl_api")
    async def dhl_writeback(booking: BookingRequest) -> BookingConfirmation:
        ...

If no adapter is registered for a target, the engine logs the booking
details and returns a pending-confirmation response (safe default).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Awaitable
import httpx

logger = logging.getLogger(__name__)


@dataclass
class BookingRequest:
    event_id: str
    carrier_name: str
    carrier_id: str
    mode: str
    estimated_cost: float
    transit_days: int
    shipment_id: str
    affected_skus: list[dict]
    hard_deadline: str
    reviewer_note: str = ""
    metadata: dict = field(default_factory=dict)


@dataclass
class BookingConfirmation:
    event_id: str
    booking_reference: str
    carrier_name: str
    status: str          # confirmed / pending / failed
    confirmed_at: str
    message: str = ""


# Registry: target_system -> async writeback function
_WRITEBACKS: dict[str, Callable[[BookingRequest], Awaitable[BookingConfirmation]]] = {}


def register_writeback(target_system: str) -> Callable:
    """Decorator that registers an async writeback for a named TMS target."""
    def decorator(fn: Callable) -> Callable:
        _WRITEBACKS[target_system.lower()] = fn
        return fn
    return decorator


async def execute_writeback(
    target_system: str,
    booking: BookingRequest,
) -> BookingConfirmation:
    """
    Execute the registered writeback for target_system.
    Falls back to the log-only adapter if no custom one is registered.
    """
    fn = _WRITEBACKS.get(target_system.lower(), _log_only_writeback)
    return await fn(booking)


async def _log_only_writeback(booking: BookingRequest) -> BookingConfirmation:
    """
    Default adapter — logs the booking and returns a pending confirmation.
    Used when no TMS integration is configured yet.
    """
    logger.info(
        "BOOKING PENDING CONFIRMATION | event=%s carrier=%s mode=%s cost=%.0f",
        booking.event_id,
        booking.carrier_name,
        booking.mode,
        booking.estimated_cost,
    )
    return BookingConfirmation(
        event_id=booking.event_id,
        booking_reference=f"PENDING-{booking.event_id[:8].upper()}",
        carrier_name=booking.carrier_name,
        status="pending",
        confirmed_at=datetime.now(timezone.utc).isoformat(),
        message="No TMS adapter configured — booking logged for manual processing.",
    )


# ── Built-in adapters ─────────────────────────────────────────────────────────

@register_writeback("generic_http")
async def _generic_http_writeback(booking: BookingRequest) -> BookingConfirmation:
    """
    Generic HTTP POST adapter. Reads TMS_WEBHOOK_URL from environment.
    Useful for any TMS that accepts a JSON webhook.
    """
    import os
    webhook_url = os.environ.get("TMS_WEBHOOK_URL", "")
    if not webhook_url:
        return await _log_only_writeback(booking)

    payload = {
        "event_id": booking.event_id,
        "shipment_id": booking.shipment_id,
        "carrier_name": booking.carrier_name,
        "carrier_id": booking.carrier_id,
        "mode": booking.mode,
        "estimated_cost": booking.estimated_cost,
        "transit_days": booking.transit_days,
        "hard_deadline": booking.hard_deadline,
        "affected_skus": booking.affected_skus,
        "reviewer_note": booking.reviewer_note,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(webhook_url, json=payload)
            response.raise_for_status()
            data = response.json()
            return BookingConfirmation(
                event_id=booking.event_id,
                booking_reference=data.get("booking_reference", ""),
                carrier_name=booking.carrier_name,
                status="confirmed",
                confirmed_at=datetime.now(timezone.utc).isoformat(),
                message=data.get("message", "Booking confirmed via generic HTTP adapter."),
            )
    except httpx.HTTPError as exc:
        logger.error("TMS writeback failed for event %s: %s", booking.event_id, exc)
        return BookingConfirmation(
            event_id=booking.event_id,
            booking_reference="",
            carrier_name=booking.carrier_name,
            status="failed",
            confirmed_at=datetime.now(timezone.utc).isoformat(),
            message=f"HTTP error: {exc}",
        )


@register_writeback("dhl_api")
async def _dhl_api_writeback(booking: BookingRequest) -> BookingConfirmation:
    """
    DHL Express API adapter stub.
    Replace the stub body with real DHL shipment creation API calls.
    """
    import os
    api_key = os.environ.get("DHL_API_KEY", "")
    if not api_key:
        logger.warning("DHL_API_KEY not set — falling back to log-only adapter")
        return await _log_only_writeback(booking)

    # Stub: in production, call DHL Shipment Tracking / Booking API here
    logger.info("DHL booking stub called for event %s", booking.event_id)
    return BookingConfirmation(
        event_id=booking.event_id,
        booking_reference=f"DHL-{booking.event_id[:8].upper()}",
        carrier_name="DHL Express",
        status="confirmed",
        confirmed_at=datetime.now(timezone.utc).isoformat(),
        message="DHL booking stub — replace with real API call.",
    )

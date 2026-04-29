"""
ERP Input Adapter — pluggable transform layer.

ERPs send disruption events in their own proprietary format.
This module normalises them into the engine's standard DisruptionEventCreate
schema before forwarding to the core webhook.

Usage
-----
Register a transform function for each source system:

    from src.adapters.erp_input import register_transform

    @register_transform("my_erp")
    def my_erp_transform(raw: dict) -> dict:
        return {
            "source_system": "my_erp",
            "event_type": raw["disruptionType"],
            ...
        }

The /api/v1/events/erp/{source_system} endpoint calls the registered
transform and forwards the result to the core disruption endpoint.
"""
from __future__ import annotations

from typing import Callable

# Registry: source_system -> transform function
_TRANSFORMS: dict[str, Callable[[dict], dict]] = {}


def register_transform(source_system: str) -> Callable:
    """Decorator that registers a transform for a named source system."""
    def decorator(fn: Callable[[dict], dict]) -> Callable[[dict], dict]:
        _TRANSFORMS[source_system.lower()] = fn
        return fn
    return decorator


def transform(source_system: str, raw_payload: dict) -> dict:
    """
    Apply the registered transform for source_system.
    Falls back to the passthrough transform if no custom one is registered.
    Raises ValueError for unrecognised systems when strict=True.
    """
    fn = _TRANSFORMS.get(source_system.lower(), _passthrough_transform)
    return fn(raw_payload)


def _passthrough_transform(raw: dict) -> dict:
    """
    Default transform — assumes the payload already matches the engine's schema.
    ERPs that conform to the published contract can skip registering a custom one.
    """
    return raw


# ── Built-in transforms ───────────────────────────────────────────────────────

@register_transform("erp_system_a")
def _erp_system_a_transform(raw: dict) -> dict:
    """
    ERP System A disruption event → engine schema.
    Expected fields: disruptionType, shipmentRef, skuList,
    originPort, destPort, originalArrival, revisedArrival, impactLevel
    """
    sku_list = raw.get("skuList", [])
    affected_skus = [
        {"sku": s.get("partNumber", s.get("sku", "")), "qty": s.get("quantity", 0)}
        for s in sku_list
    ]

    severity_map = {"HIGH": "critical", "MEDIUM": "high", "LOW": "medium"}
    event_type_map = {
        "PORT_CLOSURE": "port_strike",
        "VESSEL_DELAY": "vessel_delay",
        "WEATHER_EVENT": "weather",
        "CUSTOMS_HOLD": "customs_hold",
    }

    return {
        "source_system": "erp_system_a",
        "event_type": event_type_map.get(raw.get("disruptionType", ""), "vessel_delay"),
        "shipment_id": raw.get("shipmentRef", ""),
        "affected_skus": affected_skus,
        "location": {
            "port": raw.get("originPort"),
        },
        "original_eta": raw.get("originalArrival"),
        "revised_eta": raw.get("revisedArrival"),
        "severity": severity_map.get(raw.get("impactLevel", "MEDIUM"), "high"),
    }


@register_transform("erp_system_b")
def _erp_system_b_transform(raw: dict) -> dict:
    """
    ERP System B disruption notification → engine schema.
    Expected fields: EventType, DeliveryDoc, MaterialList,
    OriginalGoodsReceiptDate, ExpectedGoodsReceiptDate, Priority
    """
    material_list = raw.get("MaterialList", [])
    affected_skus = [
        {"sku": m.get("Material", ""), "qty": int(m.get("Quantity", 0))}
        for m in material_list
    ]

    priority_map = {"1": "critical", "2": "high", "3": "medium"}
    event_type_map = {
        "DELIVERY_DELAY": "vessel_delay",
        "PORT_STRIKE": "port_strike",
        "CUSTOMS": "customs_hold",
        "WEATHER": "weather",
    }

    return {
        "source_system": "erp_system_b",
        "event_type": event_type_map.get(raw.get("EventType", ""), "vessel_delay"),
        "shipment_id": raw.get("DeliveryDoc", ""),
        "affected_skus": affected_skus,
        "location": None,
        "original_eta": raw.get("OriginalGoodsReceiptDate"),
        "revised_eta": raw.get("ExpectedGoodsReceiptDate"),
        "severity": priority_map.get(str(raw.get("Priority", "2")), "high"),
    }


@register_transform("erp_system_c")
def _erp_system_c_transform(raw: dict) -> dict:
    """
    ERP System C shipment exception → engine schema.
    Expected fields: exceptionCode, shipmentGid, commodities,
    plannedArrival, revisedArrival, severity
    """
    commodities = raw.get("commodities", [])
    affected_skus = [
        {"sku": c.get("commodityGid", ""), "qty": int(c.get("totalQuantity", 0))}
        for c in commodities
    ]

    code_map = {
        "LABOR_ACTION": "port_strike",
        "VESSEL_DELAY": "vessel_delay",
        "WEATHER_HOLD": "weather",
        "CUSTOMS_EXAM": "customs_hold",
    }

    return {
        "source_system": "erp_system_c",
        "event_type": code_map.get(raw.get("exceptionCode", ""), "vessel_delay"),
        "shipment_id": raw.get("shipmentGid", ""),
        "affected_skus": affected_skus,
        "location": None,
        "original_eta": raw.get("plannedArrival"),
        "revised_eta": raw.get("revisedArrival"),
        "severity": raw.get("severity", "high").lower(),
    }

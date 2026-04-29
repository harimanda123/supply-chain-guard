from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from enum import Enum


class EventType(str, Enum):
    port_strike = "port_strike"
    vessel_delay = "vessel_delay"
    weather = "weather"
    customs_hold = "customs_hold"


class Severity(str, Enum):
    critical = "critical"
    high = "high"
    medium = "medium"


class AffectedSKU(BaseModel):
    sku: str
    qty: int


class Location(BaseModel):
    lat: Optional[float] = None
    lng: Optional[float] = None
    port: Optional[str] = None


class DisruptionEventCreate(BaseModel):
    source_system: str = Field(..., example="kinaxis")
    event_type: EventType
    shipment_id: str = Field(..., example="SHP-20240427-001")
    affected_skus: list[AffectedSKU]
    location: Optional[Location] = None
    original_eta: Optional[datetime] = None
    revised_eta: Optional[datetime] = None
    severity: Severity


class DisruptionEventResponse(BaseModel):
    event_id: str
    source_system: str
    event_type: str
    shipment_id: str
    affected_skus: list
    location: Optional[dict] = None
    original_eta: Optional[datetime] = None
    revised_eta: Optional[datetime] = None
    severity: str
    status: str
    received_at: datetime

    model_config = {"from_attributes": True}
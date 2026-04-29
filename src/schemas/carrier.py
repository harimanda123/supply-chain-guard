from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class CarrierCreate(BaseModel):
    carrier_name: str = Field(..., example="Express Air Freight")
    mode: str = Field(..., example="air")
    origin_port: Optional[str] = Field(None, example="CNSHA")
    dest_port: Optional[str] = Field(None, example="USLAX")
    transit_days: int = Field(..., ge=0)
    rate_per_unit: float = Field(..., ge=0.0)
    availability_date: Optional[datetime] = None
    reliability_score: float = Field(default=0.0, ge=0.0, le=100.0)


class CarrierResponse(BaseModel):
    carrier_id: str
    carrier_name: str
    mode: str
    origin_port: Optional[str] = None
    dest_port: Optional[str] = None
    transit_days: int
    rate_per_unit: float
    availability_date: Optional[datetime] = None
    reliability_score: float
    last_updated_at: datetime

    model_config = {"from_attributes": True}


class FinancialRuleCreate(BaseModel):
    sku_id: Optional[str] = Field(None, example="SKU-9921")
    max_expedite_budget: float = Field(..., ge=0.0, example=15000.0)
    auto_approve_ceiling: float = Field(..., ge=0.0, example=5000.0)
    penalty_per_day: float = Field(..., ge=0.0, example=50000.0)
    baseline_freight_cost: float = Field(default=0.0, ge=0.0)
    currency: str = Field(default="USD", example="USD")


class FinancialRuleResponse(BaseModel):
    rule_id: str
    sku_id: Optional[str] = None
    max_expedite_budget: float
    auto_approve_ceiling: float
    penalty_per_day: float
    baseline_freight_cost: float
    currency: str

    model_config = {"from_attributes": True}


class ComplianceRegistryCreate(BaseModel):
    carrier_id: str
    is_blacklisted: bool = False
    insurance_valid: bool = True
    insurance_expiry: Optional[datetime] = None
    certifications: Optional[dict] = None


class ComplianceRegistryResponse(BaseModel):
    entry_id: str
    carrier_id: str
    is_blacklisted: bool
    insurance_valid: bool
    insurance_expiry: Optional[datetime] = None
    certifications: Optional[dict] = None
    last_verified_at: datetime

    model_config = {"from_attributes": True}
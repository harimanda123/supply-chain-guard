from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class AgentAuditEntry(BaseModel):
    agent: str
    finding: str
    decision: str


class ResolutionPlan(BaseModel):
    event_id: str
    recommended_carrier: str
    recommended_mode: str
    estimated_cost: float
    estimated_eta_days: int
    cost_vs_penalty: str
    audit_trail: list[AgentAuditEntry]
    status: str = "pending_approval"
    created_at: datetime = Field(
        default_factory=datetime.utcnow
    )


class ApprovalRequest(BaseModel):
    event_id: str
    approved: bool
    reviewer_note: Optional[str] = None


class ApprovalResponse(BaseModel):
    event_id: str
    status: str
    message: str
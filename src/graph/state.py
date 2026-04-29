from typing import Optional, TypedDict


class AgentAuditEntry(TypedDict):
    agent: str
    finding: str
    decision: str


class SupplyChainState(TypedDict):
    # ── Disruption event ──────────────────────────────────────────
    event_id: str
    source_system: str
    shipment_id: str
    affected_skus: list[dict]
    delay_days: int
    severity: str

    # ── Inventory assessment ──────────────────────────────────────
    on_hand_qty: int
    safety_stock_qty: int
    days_of_cover: float
    days_of_buffer: int
    hard_deadline: str
    shutdown_cost_per_day: float
    can_wait: bool
    urgency_level: str

    # ── Route proposal ────────────────────────────────────────────
    proposed_carrier_name: str
    proposed_carrier_id: str
    proposed_mode: str
    proposed_cost: float
    proposed_transit_days: int
    carrier_options: list[dict]

    # ── Financial decision ────────────────────────────────────────
    max_expedite_budget: float
    penalty_per_day: float
    auto_approve_ceiling: float
    financially_approved: bool
    savings_achieved: float
    cost_vs_penalty_summary: str

    # ── Compliance check ──────────────────────────────────────────
    is_blacklisted: bool
    insurance_valid: bool
    insurance_expiry: str
    reliability_score: float
    certifications: dict
    compliance_cleared: bool
    compliance_checks_passed: list[str]
    compliance_checks_failed: list[str]

    # ── Loop control ──────────────────────────────────────────────
    iteration: int
    max_iterations: int

    # ── Final resolution ──────────────────────────────────────────
    resolution_status: str  # pending / approved / rejected / escalated
    audit_trail: list[AgentAuditEntry]
    error_message: Optional[str]
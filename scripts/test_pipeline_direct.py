"""Direct pipeline test to expose crash."""
from src.graph.pipeline import pipeline

state = {
    "event_id": "test-001",
    "source_system": "manual",
    "shipment_id": "SHP-TEST",
    "affected_skus": [{"sku": "SKU-9921", "qty": 500}],
    "delay_days": 5,
    "severity": "critical",
    "on_hand_qty": 150,
    "safety_stock_qty": 200,
    "days_of_cover": 3.0,
    "days_of_buffer": 0,
    "hard_deadline": "2026-05-03",
    "shutdown_cost_per_day": 50000.0,
    "can_wait": False,
    "urgency_level": "critical",
    "proposed_carrier_name": "",
    "proposed_carrier_id": "",
    "proposed_mode": "",
    "proposed_cost": 0.0,
    "proposed_transit_days": 0,
    "carrier_options": [],
    "max_expedite_budget": 15000.0,
    "penalty_per_day": 50000.0,
    "auto_approve_ceiling": 5000.0,
    "financially_approved": False,
    "savings_achieved": 0.0,
    "cost_vs_penalty_summary": "",
    "is_blacklisted": False,
    "insurance_valid": True,
    "insurance_expiry": "2027-06-30",
    "reliability_score": 92.0,
    "certifications": {},
    "compliance_cleared": False,
    "compliance_checks_passed": [],
    "compliance_checks_failed": [],
    "iteration": 1,
    "max_iterations": 5,
    "resolution_status": "processing",
    "audit_trail": [],
    "error_message": None,
}
print("Invoking pipeline...")
try:
    result = pipeline.invoke(state)
    print("Status:", result.get("resolution_status"))
except Exception as e:
    import traceback
    traceback.print_exc()

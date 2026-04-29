"""
Export JSON schemas for all ERP-facing API contracts.
Outputs to schemas/ directory at project root.
"""
import sys, json, pathlib
sys.stdout.reconfigure(encoding="utf-8")

from src.schemas.disruption import DisruptionEventCreate, DisruptionEventResponse
from src.schemas.resolution import ResolutionPlan, ApprovalRequest, ApprovalResponse
from src.schemas.carrier import CarrierResponse

out = pathlib.Path("schemas")
out.mkdir(exist_ok=True)

exports = {
    "disruption-event-create": DisruptionEventCreate,
    "disruption-event-response": DisruptionEventResponse,
    "resolution-plan": ResolutionPlan,
    "approval-request": ApprovalRequest,
    "approval-response": ApprovalResponse,
    "carrier": CarrierResponse,
}

for name, model in exports.items():
    schema = model.model_json_schema()
    path = out / f"{name}.json"
    path.write_text(json.dumps(schema, indent=2), encoding="utf-8")
    print(f"  wrote {path}")

print("Done.")

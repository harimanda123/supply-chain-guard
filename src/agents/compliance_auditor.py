import yaml
from src.config import get_llm
from src.graph.state import SupplyChainState, AgentAuditEntry
from src.tools.compliance_tools import COMPLIANCE_TOOLS, check_carrier_compliance

with open("config/agents.yaml") as f:
    AGENTS = yaml.safe_load(f)

with open("config/tasks.yaml") as f:
    TASKS = yaml.safe_load(f)

AGENT_CFG = AGENTS["compliance_auditor"]
TASK_CFG = TASKS["audit_compliance"]


def compliance_auditor_node(state: SupplyChainState) -> SupplyChainState:
    llm = get_llm()

    # ── Fetch live compliance data from DB ──────────────────────────────────
    carrier_id = state.get("proposed_carrier_id", "")
    comp_data = check_carrier_compliance.invoke({"carrier_id": carrier_id}) if carrier_id else {}

    is_blacklisted = comp_data.get("is_blacklisted", state.get("is_blacklisted", False))
    insurance_valid = comp_data.get("insurance_valid", state.get("insurance_valid", True))
    insurance_expiry = comp_data.get("insurance_expiry") or state.get("insurance_expiry", "N/A")
    certifications = comp_data.get("certifications", state.get("certifications", {}))

    # reliability_score lives on the carrier row, not compliance
    reliability_score = state.get("reliability_score", 0)

    prompt = f"""
You are a {AGENT_CFG['role']}.
Your goal: {AGENT_CFG['goal']}
Background: {AGENT_CFG['backstory']}

Task: {TASK_CFG['description'].format(
    carrier_name=state["proposed_carrier_name"],
    carrier_id=carrier_id,
    is_blacklisted=is_blacklisted,
    insurance_valid=insurance_valid,
    insurance_expiry=insurance_expiry,
    reliability_score=reliability_score,
    certifications=certifications,
)}

Expected output: {TASK_CFG['expected_output']}

Respond with: cleared (yes/no), checks_passed, checks_failed, risk_rating.
"""

    response = llm.invoke(prompt)
    finding = response.content

    checks_passed = []
    checks_failed = []

    if not is_blacklisted:
        checks_passed.append("Not blacklisted")
    else:
        checks_failed.append("Carrier is blacklisted")

    if insurance_valid:
        checks_passed.append("Insurance valid")
    else:
        checks_failed.append("Insurance invalid or expired")

    if reliability_score >= 70:
        checks_passed.append(f"Reliability score {reliability_score}/100")
    else:
        checks_failed.append(f"Reliability score too low: {reliability_score}/100")

    if not comp_data.get("found", True):
        checks_failed.append("No compliance record on file — manual review required")

    compliance_cleared = len(checks_failed) == 0

    audit_entry: AgentAuditEntry = {
        "agent": "Compliance Auditor",
        "finding": finding[:300],
        "decision": f"{'CLEARED' if compliance_cleared else 'BLOCKED'} — "
                    f"passed: {checks_passed} | failed: {checks_failed}",
    }

    return {
        **state,
        "is_blacklisted": is_blacklisted,
        "insurance_valid": insurance_valid,
        "insurance_expiry": insurance_expiry,
        "certifications": certifications,
        "compliance_cleared": compliance_cleared,
        "compliance_checks_passed": checks_passed,
        "compliance_checks_failed": checks_failed,
        "audit_trail": state.get("audit_trail", []) + [audit_entry],
    }

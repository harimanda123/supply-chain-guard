import yaml
from src.config import get_llm
from src.graph.state import SupplyChainState, AgentAuditEntry

with open("config/agents.yaml") as f:
    AGENTS = yaml.safe_load(f)

with open("config/tasks.yaml") as f:
    TASKS = yaml.safe_load(f)

AGENT_CFG = AGENTS["compliance_auditor"]
TASK_CFG = TASKS["audit_compliance"]


def compliance_auditor_node(state: SupplyChainState) -> SupplyChainState:
    llm = get_llm()

    prompt = f"""
You are a {AGENT_CFG['role']}.
Your goal: {AGENT_CFG['goal']}
Background: {AGENT_CFG['backstory']}

Task: {TASK_CFG['description'].format(
    carrier_name=state["proposed_carrier_name"],
    carrier_id=state["proposed_carrier_id"],
    is_blacklisted=state.get("is_blacklisted", False),
    insurance_valid=state.get("insurance_valid", True),
    insurance_expiry=state.get("insurance_expiry", "N/A"),
    reliability_score=state.get("reliability_score", 0),
    certifications=state.get("certifications", {}),
)}

Expected output: {TASK_CFG['expected_output']}

Respond with: cleared (yes/no), checks_passed, checks_failed, risk_rating.
"""

    response = llm.invoke(prompt)
    finding = response.content

    # Compliance logic
    checks_passed = []
    checks_failed = []

    if not state.get("is_blacklisted", False):
        checks_passed.append("Not blacklisted")
    else:
        checks_failed.append("Carrier is blacklisted")

    if state.get("insurance_valid", True):
        checks_passed.append("Insurance valid")
    else:
        checks_failed.append("Insurance invalid or expired")

    if state.get("reliability_score", 0) >= 70:
        checks_passed.append(
            f"Reliability score {state.get('reliability_score')}/100"
        )
    else:
        checks_failed.append(
            f"Reliability score too low: {state.get('reliability_score')}/100"
        )

    compliance_cleared = len(checks_failed) == 0

    audit_entry: AgentAuditEntry = {
        "agent": "Compliance Auditor",
        "finding": finding[:300],
        "decision": f"{'CLEARED' if compliance_cleared else 'BLOCKED'} — "
                    f"passed: {checks_passed} | failed: {checks_failed}",
    }

    return {
        **state,
        "compliance_cleared": compliance_cleared,
        "compliance_checks_passed": checks_passed,
        "compliance_checks_failed": checks_failed,
        "audit_trail": state.get("audit_trail", []) + [audit_entry],
    }
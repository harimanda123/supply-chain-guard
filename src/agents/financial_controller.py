import yaml
from src.config import get_llm
from src.graph.state import SupplyChainState, AgentAuditEntry
from src.tools.financial_tools import FINANCIAL_TOOLS, query_financial_rules

with open("config/agents.yaml") as f:
    AGENTS = yaml.safe_load(f)

with open("config/tasks.yaml") as f:
    TASKS = yaml.safe_load(f)

AGENT_CFG = AGENTS["financial_controller"]
TASK_CFG = TASKS["validate_financials"]


def financial_controller_node(state: SupplyChainState) -> SupplyChainState:
    llm = get_llm()

    # ── Fetch live financial rules from DB ────────────────────────────────────
    first_sku = state["affected_skus"][0]["sku"] if state["affected_skus"] else ""
    rule_data = query_financial_rules.invoke({"sku_id": first_sku}) if first_sku else {}

    max_expedite_budget = rule_data.get("max_expedite_budget", state["max_expedite_budget"])
    penalty_per_day = rule_data.get("penalty_per_day", state["penalty_per_day"])
    auto_approve_ceiling = rule_data.get("auto_approve_ceiling", state["auto_approve_ceiling"])

    prompt = f"""
You are a {AGENT_CFG['role']}.
Your goal: {AGENT_CFG['goal']}
Background: {AGENT_CFG['backstory']}

Task: {TASK_CFG['description'].format(
    carrier_name=state["proposed_carrier_name"],
    mode=state["proposed_mode"],
    estimated_cost=state["proposed_cost"],
    transit_days=state["proposed_transit_days"],
    max_expedite_budget=max_expedite_budget,
    penalty_per_day=penalty_per_day,
    auto_approve_ceiling=auto_approve_ceiling,
)}

Expected output: {TASK_CFG['expected_output']}

Respond with: approved (yes/no), cost_vs_penalty_summary, savings_achieved, reasoning.
"""

    response = llm.invoke(prompt)
    finding = response.content

    cost = state["proposed_cost"]
    days_at_risk = max(1, state["delay_days"] - state["days_of_buffer"])
    total_penalty = penalty_per_day * days_at_risk
    savings = total_penalty - cost
    financially_approved = cost <= max_expedite_budget and savings > 0

    summary = (
        f"Cost ${cost:,.0f} vs penalty ${total_penalty:,.0f} "
        f"({'APPROVED' if financially_approved else 'REJECTED'}) — "
        f"savings ${savings:,.0f}"
    )

    audit_entry: AgentAuditEntry = {
        "agent": "Financial Controller",
        "finding": finding[:300],
        "decision": summary,
    }

    return {
        **state,
        "max_expedite_budget": max_expedite_budget,
        "penalty_per_day": penalty_per_day,
        "auto_approve_ceiling": auto_approve_ceiling,
        "financially_approved": financially_approved,
        "savings_achieved": savings,
        "cost_vs_penalty_summary": summary,
        "audit_trail": state.get("audit_trail", []) + [audit_entry],
    }

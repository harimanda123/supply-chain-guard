import yaml
from src.config import get_llm
from src.graph.state import SupplyChainState, AgentAuditEntry
from src.tools.inventory_tools import INVENTORY_TOOLS, query_inventory_position, query_production_schedule

with open("config/agents.yaml") as f:
    AGENTS = yaml.safe_load(f)

with open("config/tasks.yaml") as f:
    TASKS = yaml.safe_load(f)

AGENT_CFG = AGENTS["inventory_analyst"]
TASK_CFG = TASKS["assess_inventory_impact"]


def inventory_analyst_node(state: SupplyChainState) -> SupplyChainState:
    llm = get_llm()

    affected_skus = ", ".join(
        [f"{s['sku']} (qty: {s['qty']})" for s in state["affected_skus"]]
    )
    first_sku = state["affected_skus"][0]["sku"] if state["affected_skus"] else None

    # ── Fetch live data from DB via tools ───────────────────────────────────
    inv_data = {}
    sched_data = {}
    if first_sku:
        inv_data = query_inventory_position.invoke({"sku_id": first_sku}) or {}
        sched_data = query_production_schedule.invoke({"sku_id": first_sku}) or {}

    # Prefer live DB data; fall back to state values pre-loaded by the pipeline
    on_hand_qty = inv_data.get("on_hand_qty", state["on_hand_qty"])
    safety_stock_qty = inv_data.get("safety_stock_qty", state["safety_stock_qty"])
    days_of_cover = inv_data.get("days_of_cover", state["days_of_cover"])
    shutdown_cost_per_day = sched_data.get(
        "shutdown_cost_per_day", state["shutdown_cost_per_day"]
    )
    hard_deadline = (
        sched_data.get("hard_deadline") or state["hard_deadline"]
    )
    if hard_deadline and "T" in hard_deadline:
        hard_deadline = hard_deadline.split("T")[0]  # keep date only

    prompt = f"""
You are a {AGENT_CFG['role']}.
Your goal: {AGENT_CFG['goal']}
Background: {AGENT_CFG['backstory']}

Task: {TASK_CFG['description'].format(
    affected_skus=affected_skus,
    delay_days=state["delay_days"],
    on_hand_qty=on_hand_qty,
    safety_stock_qty=safety_stock_qty,
    days_of_cover=days_of_cover,
    hard_deadline=hard_deadline,
    shutdown_cost_per_day=shutdown_cost_per_day,
)}

Expected output: {TASK_CFG['expected_output']}

Respond in plain text with clear findings.
"""

    response = llm.invoke(prompt)
    finding = response.content

    days_of_buffer = max(0, int(days_of_cover) - state["delay_days"])
    can_wait = days_of_buffer > 0
    urgency_level = "critical" if days_of_buffer <= 0 else (
        "high" if days_of_buffer <= 1 else "medium"
    )

    audit_entry: AgentAuditEntry = {
        "agent": "Inventory Analyst",
        "finding": finding[:300],
        "decision": f"can_wait={can_wait}, urgency={urgency_level}, "
                    f"days_of_buffer={days_of_buffer}",
    }

    return {
        **state,
        "on_hand_qty": on_hand_qty,
        "safety_stock_qty": safety_stock_qty,
        "days_of_cover": days_of_cover,
        "shutdown_cost_per_day": shutdown_cost_per_day,
        "hard_deadline": hard_deadline,
        "days_of_buffer": days_of_buffer,
        "can_wait": can_wait,
        "urgency_level": urgency_level,
        "audit_trail": state.get("audit_trail", []) + [audit_entry],
    }

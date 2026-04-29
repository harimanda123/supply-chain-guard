import yaml
from src.config import get_llm
from src.graph.state import SupplyChainState, AgentAuditEntry
from src.tools.carrier_tools import CARRIER_TOOLS, query_carriers

with open("config/agents.yaml") as f:
    AGENTS = yaml.safe_load(f)

with open("config/tasks.yaml") as f:
    TASKS = yaml.safe_load(f)

AGENT_CFG = AGENTS["logistics_strategist"]
TASK_CFG = TASKS["find_alternate_route"]


def logistics_strategist_node(state: SupplyChainState) -> SupplyChainState:
    llm = get_llm().bind_tools(CARRIER_TOOLS)

    # ── Fetch live carriers from DB; fall back to state pre-loaded options ──────
    live_carriers = query_carriers.invoke({}) or []
    carrier_options = live_carriers if live_carriers else state.get("carrier_options", [])

    carrier_options_text = "\n".join([
        f"- {c['carrier_name']} | mode: {c['mode']} | "
        f"cost: ${c['rate_per_unit']} | transit: {c['transit_days']} days | "
        f"reliability: {c['reliability_score']}/100"
        for c in carrier_options
    ]) or "No pre-loaded carriers. Suggest best industry-standard options."

    prompt = f"""
You are a {AGENT_CFG['role']}.
Your goal: {AGENT_CFG['goal']}
Background: {AGENT_CFG['backstory']}

Task: {TASK_CFG['description'].format(
    hard_deadline=state["hard_deadline"],
    days_of_buffer=state["days_of_buffer"],
    carrier_options=carrier_options_text,
)}

Expected output: {TASK_CFG['expected_output']}

Iteration {state.get('iteration', 1)} of {state.get('max_iterations', 5)}.
{"Previous proposal was rejected by Financial Controller. Find a more cost-effective option."
 if state.get('iteration', 1) > 1 else ""}

Respond with: carrier_name, mode, estimated_cost, transit_days, and reasoning.
"""

    response = llm.invoke(prompt)
    finding = response.content

    # Deterministic carrier selection from available options
    options = carrier_options
    if options:
        viable = [
            c for c in options
            if c["transit_days"] <= (state["days_of_buffer"] + state["delay_days"])
        ]
        # On re-iterations pick pricier-but-faster if cheaper failed; sort ascending by cost
        sort_key = "rate_per_unit"
        best = sorted(viable, key=lambda x: x[sort_key])[0] if viable \
            else sorted(options, key=lambda x: x[sort_key])[0]

        proposed_carrier_name = best["carrier_name"]
        proposed_carrier_id = best.get("carrier_id", "")
        proposed_mode = best["mode"]
        proposed_cost = best["rate_per_unit"]
        proposed_transit_days = best["transit_days"]
    else:
        proposed_carrier_name = "Industry Standard Air Freight"
        proposed_carrier_id = ""
        proposed_mode = "air"
        proposed_cost = 12000.0
        proposed_transit_days = 2

    audit_entry: AgentAuditEntry = {
        "agent": "Logistics Strategist",
        "finding": finding[:300],
        "decision": f"Proposed {proposed_carrier_name} via {proposed_mode} "
                    f"at ${proposed_cost} | {proposed_transit_days} days",
    }

    return {
        **state,
        "proposed_carrier_name": proposed_carrier_name,
        "proposed_carrier_id": proposed_carrier_id,
        "proposed_mode": proposed_mode,
        "proposed_cost": proposed_cost,
        "proposed_transit_days": proposed_transit_days,
        "carrier_options": carrier_options,
        "audit_trail": state.get("audit_trail", []) + [audit_entry],
    }
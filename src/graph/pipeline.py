from langgraph.graph import StateGraph, END

from src.graph.state import SupplyChainState
from src.agents.inventory_analyst import inventory_analyst_node
from src.agents.logistics_strategist import logistics_strategist_node
from src.agents.financial_controller import financial_controller_node
from src.agents.compliance_auditor import compliance_auditor_node
from src.agents.orchestrator import should_continue, resolve_or_escalate


def escalate_node(state: SupplyChainState) -> SupplyChainState:
    """Terminal node — max iterations reached or compliance blocked."""
    return {
        **state,
        "resolution_status": "escalated",
    }


def resolved_node(state: SupplyChainState) -> SupplyChainState:
    """Terminal node — compliance cleared, ready for human approval."""
    return {
        **state,
        "resolution_status": "pending_approval",
    }


def build_pipeline() -> StateGraph:
    graph = StateGraph(SupplyChainState)

    # ── Nodes ─────────────────────────────────────────────────────────────────
    graph.add_node("inventory_analyst", inventory_analyst_node)
    graph.add_node("logistics_strategist", logistics_strategist_node)
    graph.add_node("financial_controller", financial_controller_node)
    graph.add_node("compliance_auditor", compliance_auditor_node)
    graph.add_node("escalate", escalate_node)
    graph.add_node("resolved", resolved_node)

    # ── Entry point ───────────────────────────────────────────────────────────
    graph.set_entry_point("inventory_analyst")

    # ── Linear edges ─────────────────────────────────────────────────────────
    graph.add_edge("inventory_analyst", "logistics_strategist")
    graph.add_edge("logistics_strategist", "financial_controller")

    # ── Negotiation loop — Financial Controller decides next step ─────────────
    graph.add_conditional_edges(
        "financial_controller",
        should_continue,
        {
            "compliance_auditor": "compliance_auditor",
            "logistics_strategist": "logistics_strategist",
            "escalate": "escalate",
        },
    )

    # ── Compliance gate — resolve or escalate ─────────────────────────────────
    graph.add_conditional_edges(
        "compliance_auditor",
        resolve_or_escalate,
        {
            "resolved": "resolved",
            "escalate": "escalate",
        },
    )

    # ── Terminal nodes ────────────────────────────────────────────────────────
    graph.add_edge("resolved", END)
    graph.add_edge("escalate", END)

    return graph.compile()


# Module-level compiled graph — imported by the disruption endpoint
pipeline = build_pipeline()

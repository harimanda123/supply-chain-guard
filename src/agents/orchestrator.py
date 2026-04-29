from src.graph.state import SupplyChainState


def should_continue(state: SupplyChainState) -> str:
    """
    Router called after Financial Controller.
    Increments the iteration counter, then returns the next node name.
    """
    iteration = state.get("iteration", 1)
    max_iterations = state.get("max_iterations", 5)

    if state.get("financially_approved"):
        return "compliance_auditor"

    # Increment before checking so the strategist sees the updated count
    next_iteration = iteration + 1
    state["iteration"] = next_iteration  # mutate in-place; LangGraph re-serialises

    if next_iteration > max_iterations:
        return "escalate"

    return "logistics_strategist"


def resolve_or_escalate(state: SupplyChainState) -> str:
    """
    Router called after Compliance Auditor.
    Returns next node based on compliance result.
    """
    if state.get("compliance_cleared"):
        return "resolved"

    return "escalate"
from src.graph.state import SupplyChainState


def should_continue(state: SupplyChainState) -> str:
    """
    Router called after Financial Controller.
    Returns next node name based on approval and iteration count.
    """
    iteration = state.get("iteration", 1)
    max_iterations = state.get("max_iterations", 5)

    if state.get("financially_approved"):
        return "compliance_auditor"

    if iteration >= max_iterations:
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
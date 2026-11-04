import time

from resolve.graph.nodes.common import bump
from resolve.graph.state import TicketState


def approval_node(state: TicketState) -> TicketState:
    started = time.perf_counter()
    action = state.get("proposed_action")
    if not action or not action.get("needs_approval"):
        return bump(state, "approval", "skipped", {}, started)
    if state.get("auto_approve"):
        state["approval_decision"] = "approve"
        state["approver"] = "ci-fixture"
        return bump(state, "approval", "auto_approved", {"by": "ci-fixture"}, started)
    if state.get("approval_decision") == "approve":
        return bump(state, "approval", "approved", {"by": state.get("approver")}, started)
    if state.get("approval_decision") == "reject":
        state["status"] = "escalated"
        state["reply"] = "A reviewer rejected the proposed write. Escalated."
        return bump(state, "approval", "rejected", {"by": state.get("approver")}, started)
    state["status"] = "awaiting_approval"
    return bump(state, "approval", "interrupt", {"action": action}, started)

import time
from types import SimpleNamespace

from resolve.graph.nodes.common import bump
from resolve.graph.state import TicketState
from resolve.policy.engine import decide


def policy_gate_node(state: TicketState) -> TicketState:
    started = time.perf_counter()
    tools = state.get("tool_results") or {}
    cust = tools.get("get_customer")
    sub = tools.get("get_subscription")
    invoices = tools.get("get_invoices") or []
    incidents = tools.get("get_incidents") or []
    category = (state.get("classification") or {}).get("category", "account")
    if not cust or not sub:
        state["proposed_action"] = None
        return bump(state, "policy_gate", "skipped", {"reason": "missing account"}, started)

    customer = SimpleNamespace(**cust)
    subscription = SimpleNamespace(**sub)
    inv_ns = [SimpleNamespace(**i) for i in invoices]
    inc_ns = [SimpleNamespace(**i) for i in incidents]
    decision = decide(
        customer,
        subscription,
        inv_ns,
        inc_ns,
        category,
        state.get("raw_text") or "",
    )
    flags = state.get("injection_flags") or []
    if flags and decision.allowed:
        # Writes cannot originate from injected instructions
        hostile = {"ignore-previous", "forced-approve", "forced-refund", "jailbreak", "xml-override", "system-role"}
        if set(flags) & hostile:
            decision_dict = None
            payload = {"blocked": True, "flags": flags}
            state["proposed_action"] = None
            return bump(state, "policy_gate", "blocked_injection", payload, started)

    action = None
    if decision.allowed and decision.action_type:
        action = {
            "type": decision.action_type,
            "amount_usd": decision.amount_usd,
            "needs_approval": decision.needs_approval,
            "rule_ids": decision.rule_ids,
            "reason": decision.reason,
        }
    state["proposed_action"] = action
    return bump(state, "policy_gate", "decision", action or {"allowed": False, "reason": decision.reason}, started)

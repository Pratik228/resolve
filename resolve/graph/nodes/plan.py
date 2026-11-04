import time

from resolve.graph.nodes.common import bump
from resolve.graph.state import TicketState
from resolve.tools.registry import REGISTRY


def plan_node(state: TicketState) -> TicketState:
    started = time.perf_counter()
    category = (state.get("classification") or {}).get("category", "account")
    text = (state.get("redacted_text") or "").lower()
    tools = ["get_customer"]
    if category in {"billing"} or "invoice" in text or "refund" in text or "charged" in text:
        tools.append("get_invoices")
        tools.append("get_subscription")
    if category in {"sla"} or "uptime" in text or "incident" in text:
        tools.extend(["get_incidents", "get_subscription", "get_invoices"])
    if category in {"technical"} or "nw-" in text or "usage" in text or "quota" in text:
        tools.append("get_usage")
    # de-dupe, allow-list
    seen = []
    for name in tools:
        if name in REGISTRY and name not in seen:
            seen.append(name)
    state["plan"] = seen
    return bump(state, "plan", "tools_selected", {"tools": seen}, started)

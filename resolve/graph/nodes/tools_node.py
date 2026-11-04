import time

from resolve.graph.nodes.common import bump
from resolve.graph.state import TicketState
from resolve.tools.registry import REGISTRY


def tools_node(state: TicketState) -> TicketState:
    started = time.perf_counter()
    customer_id = state.get("customer_id")
    results: dict = {}
    if customer_id:
        for name in state.get("plan") or []:
            fn = REGISTRY[name]
            results[name] = fn(customer_id)
    state["tool_results"] = results
    summary = {k: (len(v) if isinstance(v, list) else bool(v)) for k, v in results.items()}
    return bump(state, "tools", "tool_results", summary, started)

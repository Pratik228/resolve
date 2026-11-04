import time

from resolve.graph.nodes.common import bump
from resolve.graph.state import TicketState
from resolve.guards.injection import scan


def injection_scan_node(state: TicketState) -> TicketState:
    started = time.perf_counter()
    flags = scan(state.get("redacted_text") or state["raw_text"])
    state["injection_flags"] = flags
    return bump(state, "injection_scan", "flags", {"flags": flags}, started)

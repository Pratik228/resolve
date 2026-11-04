import time

from resolve.graph.nodes.common import bump
from resolve.graph.state import TicketState
from resolve.guards.pii import redact


def redact_node(state: TicketState) -> TicketState:
    started = time.perf_counter()
    result = redact(state["raw_text"])
    state["redacted_text"] = result.redacted_text
    state["pii_map"] = result.pii_map
    return bump(state, "redact", "pii_redacted", {"tokens": list(result.pii_map)}, started)

from __future__ import annotations

import time
from typing import Any

from resolve.config import get_settings
from resolve.db.models import AuditLog
from resolve.graph.state import TicketState


def bump(state: TicketState, node: str, event: str, payload: dict[str, Any], started: float) -> TicketState:
    duration = (time.perf_counter() - started) * 1000
    state["step_count"] = int(state.get("step_count") or 0) + 1
    events = list(state.get("events") or [])
    events.append(
        {
            "node": node,
            "event": event,
            "payload": payload,
            "duration_ms": round(duration, 2),
            "step": state["step_count"],
        }
    )
    state["events"] = events
    # Buffered: the runner writes all audit rows in the same transaction as the ticket state
    # (flush_audit). One commit per ticket instead of one per node.
    pending = list(state.get("pending_audit") or [])
    pending.append({"node": node, "event": event, "payload": payload, "duration_ms": duration})
    state["pending_audit"] = pending
    if state["step_count"] >= get_settings().max_steps and state.get("status") == "running":
        state["status"] = "escalated"
        state["reply"] = "Escalated: step cap reached. A human will take this ticket."
    return state


def flush_audit(state: TicketState, session) -> None:
    for e in state.pop("pending_audit", None) or []:
        session.add(
            AuditLog(
                ticket_id=state.get("ticket_id") or "unknown",
                node=e["node"],
                event=e["event"],
                payload_json=e["payload"],
                duration_ms=e["duration_ms"],
                cost_usd=0.0,
            )
        )

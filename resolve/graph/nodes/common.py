from __future__ import annotations

import time
from typing import Any

from resolve.config import get_settings
from resolve.db.models import AuditLog
from resolve.db.session import get_session
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
    try:
        with get_session() as session:
            session.add(
                AuditLog(
                    ticket_id=state.get("ticket_id") or "unknown",
                    node=node,
                    event=event,
                    payload_json=payload,
                    duration_ms=duration,
                    cost_usd=0.0,
                )
            )
    except Exception:
        pass
    if state["step_count"] >= get_settings().max_steps and state.get("status") == "running":
        state["status"] = "escalated"
        state["reply"] = "Escalated: step cap reached. A human will take this ticket."
    return state

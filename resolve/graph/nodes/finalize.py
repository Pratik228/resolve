import hashlib
import time
import uuid

from resolve.db.models import Action, Ticket
from resolve.db.session import get_session
from resolve.graph.nodes.common import bump
from resolve.graph.state import TicketState


def idempotency_key(ticket_id: str, action_type: str, amount: float) -> str:
    raw = f"{ticket_id}:{action_type}:{amount:.2f}"
    return hashlib.sha256(raw.encode()).hexdigest()[:40]


def finalize_node(state: TicketState) -> TicketState:
    started = time.perf_counter()
    if state.get("status") == "escalated":
        return bump(state, "finalize", "skipped_escalated", {}, started)
    draft = state.get("draft") or {"text": ""}
    action = state.get("proposed_action")
    if action:
        key = idempotency_key(state["ticket_id"], action["type"], action["amount_usd"])
        with get_session() as session:
            existing = session.query(Action).filter(Action.idempotency_key == key).one_or_none()
            if existing is None:
                session.add(
                    Action(
                        id=str(uuid.uuid4())[:32],
                        ticket_id=state["ticket_id"],
                        type=action["type"],
                        amount_usd=action["amount_usd"],
                        status="executed",
                        idempotency_key=key,
                        approved_by=state.get("approver") or "auto",
                        rule_ids=action.get("rule_ids") or [],
                    )
                )
            else:
                action = {**action, "deduped": True}
        state["proposed_action"] = action
    state["status"] = "resolved"
    state["reply"] = draft.get("text") or "Resolved."
    with get_session() as session:
        row = session.get(Ticket, state["ticket_id"])
        if row:
            row.status = "resolved"
            row.reply = state["reply"]
            row.state_json = {k: v for k, v in state.items() if k != "events"}
            row.cost_usd = float(state.get("cost_usd") or 0)
    return bump(state, "finalize", "finalized", {"action": action}, started)


def escalate_node(state: TicketState) -> TicketState:
    started = time.perf_counter()
    state["status"] = "escalated"
    category = (state.get("classification") or {}).get("category")
    state["reply"] = (
        f"Escalated to a human queue ({category}). The agent will not execute writes on this ticket."
    )
    with get_session() as session:
        row = session.get(Ticket, state.get("ticket_id"))
        if row:
            row.status = "escalated"
            row.reply = state["reply"]
            row.state_json = {k: v for k, v in state.items() if k != "events"}
    return bump(state, "escalate", "escalated", {"category": category}, started)

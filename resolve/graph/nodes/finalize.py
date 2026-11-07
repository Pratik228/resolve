import hashlib
import time
import uuid

from sqlalchemy.exc import IntegrityError

from resolve.db.models import Action, Ticket
from resolve.db.session import get_session
from resolve.graph.nodes.common import bump
from resolve.graph.state import TicketState


def idempotency_key(customer_id: str | None, action_type: str, target_ref: str) -> str:
    """One payout per (customer, type, thing paid for). It used to be keyed per *ticket*, so two tickets
    about the same duplicate invoice each refunded it (453 refunds of one $49 duplicate in dev)."""
    raw = f"{customer_id}:{action_type}:{target_ref}"
    return hashlib.sha256(raw.encode()).hexdigest()[:40]


def finalize_node(state: TicketState) -> TicketState:
    started = time.perf_counter()
    if state.get("status") == "escalated":
        return bump(state, "finalize", "skipped_escalated", {}, started)
    draft = state.get("draft") or {"text": ""}
    action = state.get("proposed_action")
    if action:
        ref = action.get("target_ref") or f"ticket:{state['ticket_id']}:{action['amount_usd']:.2f}"
        key = idempotency_key(state.get("customer_id"), action["type"], ref)
        try:
            with get_session() as session:
                existing = session.query(Action).filter(Action.idempotency_key == key).one_or_none()
                if existing is None:
                    session.add(
                        Action(
                            id=str(uuid.uuid4())[:32],
                            ticket_id=state["ticket_id"],
                            customer_id=state.get("customer_id"),
                            target_ref=ref,
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
        except IntegrityError:
            # A concurrent ticket won the race on the unique key: it paid, we must not.
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

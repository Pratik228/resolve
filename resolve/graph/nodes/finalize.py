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


# Customer-facing text per escalation reason. The internal reason stays in the audit event, never in the reply.
ESCALATION_REPLY = {
    "legal": "Thanks for letting us know. Because this involves a legal matter, our legal team will handle it "
    "directly and will contact you. No changes have been made to your account in the meantime.",
    "deletion": "We've received your deletion request. Our privacy team handles account and data erasure and will "
    "confirm the scope and timing with you directly. Nothing has been deleted yet.",
    "contract": "Contract and custom-terms changes are handled by your account team, so I've passed this to them. "
    "They'll follow up with you; nothing on your plan has changed.",
    "chargeback": "Since a chargeback is open with your bank, our finance team owns this charge now and will follow "
    "up with you. We can't issue a separate refund while the dispute is open.",
    "out_of_scope": "I can't share or act on another customer's account or personal details. If this is about your "
    "own account, reply from the account owner's address and a teammate will help.",
}
DEFAULT_ESCALATION_REPLY = (
    "I've passed this ticket to a teammate, who will follow up with you. No changes have been made to your account."
)


def escalate_node(state: TicketState) -> TicketState:
    started = time.perf_counter()
    state["status"] = "escalated"
    category = (state.get("classification") or {}).get("category")
    state["reply"] = ESCALATION_REPLY.get(category or "", DEFAULT_ESCALATION_REPLY)
    with get_session() as session:
        row = session.get(Ticket, state.get("ticket_id"))
        if row:
            row.status = "escalated"
            row.reply = state["reply"]
            row.state_json = {k: v for k, v in state.items() if k != "events"}
    return bump(state, "escalate", "escalated", {"category": category}, started)

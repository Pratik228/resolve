from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from apps.api.ratelimit import limit
from apps.api.sse import iter_ticket_events
from resolve.db.models import Ticket
from resolve.db.session import get_session
from resolve.graph.runner import run_ticket

router = APIRouter()


class TicketIn(BaseModel):
    text: str = Field(min_length=3, max_length=4000)
    customer_id: str | None = "cus_014"
    # No auto_approve here on purpose: the public API must never let a caller skip the
    # human approval step. Only the offline eval harness calls run_ticket(auto_approve=True).


@router.post("/tickets")
def create_ticket(body: TicketIn, request: Request):
    limit(request)
    state = run_ticket(body.text, body.customer_id, auto_approve=False)
    return {
        "id": state["ticket_id"],
        "status": state["status"],
        "reply": state.get("reply"),
        "proposed_action": state.get("proposed_action"),
        "events": state.get("events"),
        "retrieved": [
            {"doc_id": c["doc_id"], "title": c.get("title"), "heading": c.get("heading")}
            for c in state.get("retrieved") or []
        ],
        "classification": state.get("classification"),
        "injection_flags": state.get("injection_flags"),
        "cost_usd": state.get("cost_usd"),
    }


@router.get("/tickets")
def list_tickets():
    with get_session() as session:
        rows = session.query(Ticket).order_by(Ticket.created_at.desc()).limit(50).all()
        return [
            {
                "id": r.id,
                "customer_id": r.customer_id,
                "raw_text": r.raw_text,
                "status": r.status,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "cost_usd": r.cost_usd,
            }
            for r in rows
        ]


@router.get("/tickets/{ticket_id}")
def get_ticket(ticket_id: str):
    with get_session() as session:
        row = session.get(Ticket, ticket_id)
        if not row:
            raise HTTPException(404)
        return {
            "id": row.id,
            "customer_id": row.customer_id,
            "raw_text": row.raw_text,
            "status": row.status,
            "reply": row.reply,
            "state": row.state_json,
            "cost_usd": row.cost_usd,
        }


@router.get("/tickets/{ticket_id}/stream")
def stream_ticket(ticket_id: str):
    return EventSourceResponse(iter_ticket_events(ticket_id))


DEMO_CUSTOMERS = ("cus_014", "cus_008", "cus_001")


@router.post("/demo/reset")
def demo_reset(request: Request):
    """Sandbox only: clear payouts for the three landing-page demo customers and expire their paused
    approvals, so every visitor sees the same first run. Real idempotency still applies within a run."""
    limit(request, per_minute=6, bucket="demo-reset")
    from resolve.db.models import Action

    with get_session() as session:
        removed = (
            session.query(Action)
            .filter(Action.customer_id.in_(DEMO_CUSTOMERS))
            .delete(synchronize_session=False)
        )
        expired = (
            session.query(Ticket)
            .filter(Ticket.customer_id.in_(DEMO_CUSTOMERS), Ticket.status == "awaiting_approval")
            .update({Ticket.status: "expired"}, synchronize_session=False)
        )
    return {"payouts_cleared": removed, "approvals_expired": expired}

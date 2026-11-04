from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from apps.api.sse import iter_ticket_events
from resolve.db.models import Ticket
from resolve.db.session import get_session
from resolve.graph.runner import run_ticket

router = APIRouter()


class TicketIn(BaseModel):
    text: str
    customer_id: str | None = "cus_014"
    auto_approve: bool = False


@router.post("/tickets")
def create_ticket(body: TicketIn):
    state = run_ticket(body.text, body.customer_id, auto_approve=body.auto_approve)
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

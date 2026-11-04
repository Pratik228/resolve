from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from resolve.db.models import Ticket
from resolve.db.session import get_session
from resolve.graph.runner import approve

router = APIRouter()


class ApprovalIn(BaseModel):
    decision: str
    approver: str = "operator"


@router.get("/approvals")
def list_approvals(status: str = "pending"):
    wanted = "awaiting_approval" if status == "pending" else status
    with get_session() as session:
        rows = session.query(Ticket).filter(Ticket.status == wanted).all()
        return [
            {
                "id": r.id,
                "customer_id": r.customer_id,
                "raw_text": r.raw_text,
                "action": (r.state_json or {}).get("proposed_action"),
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]


@router.post("/approvals/{ticket_id}")
def decide(ticket_id: str, body: ApprovalIn):
    if body.decision not in {"approve", "reject"}:
        raise HTTPException(400, "decision must be approve or reject")
    try:
        state = approve(ticket_id, body.approver, body.decision)
    except KeyError:
        raise HTTPException(404)
    return {"id": ticket_id, "status": state.get("status"), "reply": state.get("reply")}

from __future__ import annotations

import json
from collections.abc import Iterator

from resolve.db.models import AuditLog, Ticket
from resolve.db.session import get_session


def iter_ticket_events(ticket_id: str) -> Iterator[str]:
    with get_session() as session:
        ticket = session.get(Ticket, ticket_id)
        logs = (
            session.query(AuditLog)
            .filter(AuditLog.ticket_id == ticket_id)
            .order_by(AuditLog.id.asc())
            .all()
        )
        payload = {
            "ticket_id": ticket_id,
            "status": ticket.status if ticket else "unknown",
            "reply": ticket.reply if ticket else None,
            "events": [
                {
                    "id": log.id,
                    "node": log.node,
                    "event": log.event,
                    "payload": log.payload_json,
                    "duration_ms": log.duration_ms,
                    "ts": log.ts.isoformat() if log.ts else None,
                }
                for log in logs
            ],
        }
    yield f"data: {json.dumps(payload, default=str)}\n\n"

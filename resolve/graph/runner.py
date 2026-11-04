"""Explicit state machine. LangGraph wraps the same nodes in build.py."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from resolve.db.models import Ticket
from resolve.db.session import get_session, init_db
from resolve.graph.nodes.approval import approval_node
from resolve.graph.nodes.classify import classify_node
from resolve.graph.nodes.draft import draft_node
from resolve.graph.nodes.finalize import escalate_node, finalize_node
from resolve.graph.nodes.injection_scan import injection_scan_node
from resolve.graph.nodes.plan import plan_node
from resolve.graph.nodes.policy_gate import policy_gate_node
from resolve.graph.nodes.redact import redact_node
from resolve.graph.nodes.retrieve import retrieve_node
from resolve.graph.nodes.tools_node import tools_node
from resolve.graph.nodes.validate import validate_node
from resolve.graph.state import TicketState
from resolve.config import get_settings

ESCALATE_CATEGORIES = {"legal", "deletion", "contract"}


def new_ticket(raw_text: str, customer_id: str | None, auto_approve: bool = False) -> TicketState:
    init_db()
    ticket_id = "tkt_" + uuid.uuid4().hex[:12]
    with get_session() as session:
        session.add(
            Ticket(
                id=ticket_id,
                customer_id=customer_id,
                raw_text=raw_text,
                status="running",
                created_at=datetime.now(timezone.utc).replace(tzinfo=None),
                state_json={},
            )
        )
    return TicketState(
        ticket_id=ticket_id,
        customer_id=customer_id,
        raw_text=raw_text,
        redacted_text="",
        pii_map={},
        injection_flags=[],
        classification={},
        plan=[],
        retrieved=[],
        tool_results={},
        proposed_action=None,
        draft={},
        validation={},
        retries=0,
        step_count=0,
        status="running",
        cost_usd=0.0,
        reply="",
        events=[],
        auto_approve=auto_approve,
        approval_decision=None,
        approver=None,
    )


def _save(state: TicketState) -> None:
    with get_session() as session:
        row = session.get(Ticket, state["ticket_id"])
        if row:
            row.status = state.get("status") or row.status
            row.reply = state.get("reply")
            row.cost_usd = float(state.get("cost_usd") or 0)
            row.state_json = dict(state)


def run(state: TicketState) -> TicketState:
    """Run or resume. If status is awaiting_approval, jump to approval → finalize."""
    if state.get("status") == "awaiting_approval":
        state["status"] = "running"
        state = approval_node(state)
        if state.get("status") == "awaiting_approval":
            _save(state)
            return state
        if state.get("status") == "escalated":
            state = escalate_node(state)
            _save(state)
            return state
        state = finalize_node(state)
        _save(state)
        return state

    state = redact_node(state)
    state = injection_scan_node(state)
    state = classify_node(state)
    category = (state.get("classification") or {}).get("category")
    if category in ESCALATE_CATEGORIES:
        state = escalate_node(state)
        _save(state)
        return state

    state = plan_node(state)
    # Fan-out conceptually; sequential here so SQLite stays simple
    state = retrieve_node(state)
    state = tools_node(state)
    if state.get("status") == "escalated":
        _save(state)
        return state
    state = policy_gate_node(state)

    max_retries = get_settings().max_draft_retries
    while True:
        state = draft_node(state)
        state = validate_node(state)
        validation = state.get("validation") or {}
        ok = (
            validation.get("grounded")
            and validation.get("policy_ok")
            and validation.get("pii_ok")
            and validation.get("injection_ok")
        )
        if ok:
            break
        if int(state.get("retries") or 0) >= max_retries:
            state = escalate_node(state)
            _save(state)
            return state
        if state.get("status") == "escalated":
            _save(state)
            return state

    action = state.get("proposed_action")
    if action and action.get("needs_approval"):
        state = approval_node(state)
        if state.get("status") == "awaiting_approval":
            _save(state)
            return state
        if state.get("status") == "escalated":
            state = escalate_node(state)
            _save(state)
            return state

    state = finalize_node(state)
    _save(state)
    return state


def approve(ticket_id: str, approver: str, decision: str) -> TicketState:
    with get_session() as session:
        row = session.get(Ticket, ticket_id)
        if not row:
            raise KeyError(ticket_id)
        state: TicketState = dict(row.state_json)  # type: ignore[assignment]
        state["events"] = state.get("events") or []
        state["ticket_id"] = ticket_id
    state["approval_decision"] = decision
    state["approver"] = approver
    state["status"] = "awaiting_approval"
    return run(state)


def run_ticket(text: str, customer_id: str | None, auto_approve: bool = False) -> TicketState:
    return run(new_ticket(text, customer_id, auto_approve=auto_approve))

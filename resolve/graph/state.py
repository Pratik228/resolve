from __future__ import annotations

from typing import Any, Literal, TypedDict

from pydantic import BaseModel, Field


class Classification(BaseModel):
    category: Literal["billing", "technical", "account", "sla", "legal", "deletion", "contract"]
    urgency: Literal["low", "normal", "high"] = "normal"
    needs_account_data: bool = True
    needs_kb: bool = True


class Action(BaseModel):
    type: Literal["refund", "credit"]
    amount_usd: float
    needs_approval: bool
    rule_ids: list[str] = Field(default_factory=list)
    reason: str = ""


class Draft(BaseModel):
    text: str
    cited_doc_ids: list[str] = Field(default_factory=list)


class Validation(BaseModel):
    grounded: bool = True
    policy_ok: bool = True
    pii_ok: bool = True
    injection_ok: bool = True
    reasons: list[str] = Field(default_factory=list)


class TicketState(TypedDict, total=False):
    ticket_id: str
    customer_id: str | None
    raw_text: str
    redacted_text: str
    pii_map: dict[str, str]
    injection_flags: list[str]
    classification: dict[str, Any]
    plan: list[str]
    retrieved: list[dict[str, Any]]
    rewrite: dict[str, Any]
    tool_results: dict[str, Any]
    proposed_action: dict[str, Any] | None
    draft: dict[str, Any]
    validation: dict[str, Any]
    retries: int
    step_count: int
    status: Literal["running", "awaiting_approval", "resolved", "escalated"]
    cost_usd: float
    reply: str
    events: list[dict[str, Any]]
    auto_approve: bool
    approval_decision: str | None
    approver: str | None

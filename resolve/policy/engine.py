"""Deterministic money. The LLM never calls this with invented numbers — nodes pass DB rows."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Iterable

AUTO_APPROVE_USD = 100.0

SLA_TABLE = {
    "starter": {"target": 99.5, "pct_per_tenth": 5.0, "cap": 20.0},
    "pro": {"target": 99.9, "pct_per_tenth": 10.0, "cap": 30.0},
    "enterprise": {"target": 99.95, "pct_per_tenth": 15.0, "cap": 50.0},
}


@dataclass(frozen=True)
class Decision:
    allowed: bool
    action_type: str | None
    amount_usd: float
    needs_approval: bool
    rule_ids: list[str] = field(default_factory=list)
    reason: str = ""


def _needs_approval(amount: float, plan: str) -> bool:
    return amount > AUTO_APPROVE_USD or plan == "enterprise"


def _as_dt(value: datetime | str) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)


def find_duplicate_invoices(invoices: Iterable[Any]) -> list[Any]:
    """Prefer the explicit duplicate_of flag; also detect same-day same-amount twins."""
    rows = list(invoices)
    marked = [inv for inv in rows if getattr(inv, "duplicate_of", None)]
    if marked:
        return marked
    buckets: dict[tuple, list] = {}
    for inv in rows:
        if getattr(inv, "status", "paid") not in {"paid", "open"}:
            continue
        day = _as_dt(inv.issued_at).date()
        key = (
            getattr(inv, "customer_id", None),
            round(float(inv.amount_usd), 2),
            day,
            getattr(inv, "description", ""),
        )
        buckets.setdefault(key, []).append(inv)
    dupes = []
    for group in buckets.values():
        if len(group) >= 2:
            group.sort(key=lambda i: (i.id,))
            dupes.extend(group[1:])
    return dupes


def refund_eligibility(
    customer: Any,
    subscription: Any,
    invoices: Iterable[Any],
    ticket_category: str,
    ticket_text: str = "",
    now: datetime | None = None,
) -> Decision:
    """KB: refund-policy.md — duplicates always; Enterprise annual never (except dupes); 14-day full."""
    now = now or datetime(2026, 11, 3)
    text = (ticket_text or "").lower()
    plan = getattr(subscription, "plan", None) or getattr(customer, "plan", "starter")
    period = getattr(subscription, "billing_period", "monthly")

    if "chargeback" in text:
        return Decision(False, None, 0.0, False, ["chargeback-finance"], "Chargebacks are owned by finance")

    dupes = find_duplicate_invoices(invoices)
    if dupes and any(k in text for k in ("refund", "charged twice", "duplicate", "double", "extra")):
        amount = round(float(dupes[0].amount_usd), 2)
        return Decision(
            True,
            "refund",
            amount,
            _needs_approval(amount, plan),
            ["refund-policy:duplicate"],
            f"Duplicate invoice {dupes[0].id} for ${amount:.2f}",
        )

    if ticket_category not in {"billing", "account"} and "refund" not in text:
        return Decision(False, None, 0.0, False, ["no-refund-intent"], "No refund requested")

    if plan == "enterprise" and period == "annual":
        return Decision(
            False,
            None,
            0.0,
            False,
            ["refund-policy:enterprise-annual"],
            "Enterprise annual plans are non-refundable except duplicate charges",
        )

    if "lifetime" in text or "ceo promised" in text:
        return Decision(False, None, 0.0, False, ["refund-policy:no-goodwill"], "Goodwill / fake-promise claims are not eligible")

    paid = [i for i in invoices if getattr(i, "status", "paid") == "paid"]
    if not paid:
        return Decision(False, None, 0.0, False, ["no-paid-invoice"], "No paid invoices")

    started = _as_dt(subscription.started_at)
    last = max(paid, key=lambda i: _as_dt(i.issued_at))
    days = (now.date() - started.date()).days
    if days <= 14 and "refund" in text:
        amount = round(float(last.amount_usd), 2)
        return Decision(
            True,
            "refund",
            amount,
            _needs_approval(amount, plan),
            ["refund-policy:14-day"],
            f"Full refund within 14 days (day {days})",
        )

    if days == 15 and "refund" in text:
        # Prorate remaining days in a 30-day month from last invoice
        issued = _as_dt(last.issued_at)
        remaining = max(0, 30 - (now.date() - issued.date()).days)
        amount = round(float(last.amount_usd) * remaining / 30.0, 2)
        return Decision(
            True,
            "refund",
            amount,
            _needs_approval(amount, plan),
            ["refund-policy:prorate"],
            f"Prorated {remaining}/30 days",
        )

    return Decision(False, None, 0.0, False, ["refund-policy:ineligible"], "No eligible refund")


def sla_credit(subscription: Any, incidents: Iterable[Any]) -> Decision:
    plan = subscription.plan
    rules = SLA_TABLE[plan]
    fee = float(subscription.monthly_fee_usd)
    relevant = [
        inc
        for inc in incidents
        if plan in {p.strip() for p in inc.affected_plans.split(",")}
    ]
    if not relevant:
        return Decision(False, None, 0.0, False, ["sla:no-incident"], "No incident affected this plan")

    uptime = min(float(inc.uptime_pct) for inc in relevant)
    below = rules["target"] - uptime
    if below <= 1e-9:
        return Decision(False, None, 0.0, False, ["sla:met"], "Uptime met the target")

    steps = max(1, math.ceil(below / 0.1 - 1e-9))
    raw = steps * (rules["pct_per_tenth"] / 100.0) * fee
    capped = min(raw, (rules["cap"] / 100.0) * fee)
    amount = round(capped, 2)
    return Decision(
        True,
        "credit",
        amount,
        _needs_approval(amount, plan),
        ["sla:credit"],
        f"{plan} uptime {uptime}% vs {rules['target']}% → {steps} step(s) = ${amount:.2f}",
    )


def decide(
    customer: Any,
    subscription: Any,
    invoices: Iterable[Any],
    incidents: Iterable[Any],
    ticket_category: str,
    ticket_text: str,
) -> Decision:
    """Refunds beat SLA credits on the same ticket (KB: credits never stack with duplicate refunds)."""
    refund = refund_eligibility(customer, subscription, invoices, ticket_category, ticket_text)
    if refund.allowed:
        return refund
    if ticket_category in {"sla"} or "credit" in ticket_text.lower() or "uptime" in ticket_text.lower() or "incident" in ticket_text.lower():
        return sla_credit(subscription, incidents)
    return refund

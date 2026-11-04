"""Allow-listed account tools. Writes go through policy + finalize, not through the LLM."""

from __future__ import annotations

from typing import Any, Callable

from resolve.db.models import Customer, Incident, Invoice, Subscription, Usage
from resolve.db.session import get_session

ToolFn = Callable[[str], Any]


def get_customer(customer_id: str) -> dict | None:
    with get_session() as session:
        row = session.get(Customer, customer_id)
        if not row:
            return None
        return {
            "id": row.id,
            "name": row.name,
            "email": row.email,
            "plan": row.plan,
            "region": row.region,
            "created_at": row.created_at.isoformat(),
        }


def get_invoices(customer_id: str) -> list[dict]:
    with get_session() as session:
        rows = session.query(Invoice).filter(Invoice.customer_id == customer_id).all()
        return [
            {
                "id": r.id,
                "customer_id": r.customer_id,
                "amount_usd": r.amount_usd,
                "status": r.status,
                "issued_at": r.issued_at.isoformat(),
                "description": r.description,
                "duplicate_of": r.duplicate_of,
            }
            for r in rows
        ]


def get_usage(customer_id: str) -> list[dict]:
    with get_session() as session:
        rows = (
            session.query(Usage)
            .filter(Usage.customer_id == customer_id)
            .order_by(Usage.date.desc())
            .limit(14)
            .all()
        )
        return [
            {
                "date": r.date,
                "api_calls": r.api_calls,
                "errors_by_code": r.errors_by_code,
            }
            for r in rows
        ]


def get_incidents(customer_id: str) -> list[dict]:
    with get_session() as session:
        cust = session.get(Customer, customer_id)
        plan = cust.plan if cust else ""
        rows = session.query(Incident).all()
        out = []
        for r in rows:
            plans = {p.strip() for p in r.affected_plans.split(",")}
            if plan in plans or not plan:
                out.append(
                    {
                        "id": r.id,
                        "started_at": r.started_at.isoformat(),
                        "ended_at": r.ended_at.isoformat(),
                        "affected_plans": r.affected_plans,
                        "uptime_pct": r.uptime_pct,
                        "summary": r.summary,
                    }
                )
        return out


def get_subscription(customer_id: str) -> dict | None:
    with get_session() as session:
        row = (
            session.query(Subscription)
            .filter(Subscription.customer_id == customer_id)
            .first()
        )
        if not row:
            return None
        return {
            "id": row.id,
            "customer_id": row.customer_id,
            "plan": row.plan,
            "billing_period": row.billing_period,
            "status": row.status,
            "monthly_fee_usd": row.monthly_fee_usd,
            "renews_at": row.renews_at.isoformat(),
            "started_at": row.started_at.isoformat(),
        }


REGISTRY: dict[str, ToolFn] = {
    "get_customer": get_customer,
    "get_invoices": get_invoices,
    "get_usage": get_usage,
    "get_incidents": get_incidents,
    "get_subscription": get_subscription,
}

"""Idempotent seed from data/seed/*.json."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from resolve.config import get_settings
from resolve.db.models import Customer, Incident, Invoice, Subscription, Usage
from resolve.db.session import get_session, init_db


def _load(name: str) -> list:
    path = get_settings().data_dir / "seed" / name
    return json.loads(Path(path).read_text())


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


def seed() -> None:
    init_db()
    with get_session() as session:
        for row in _load("customers.json"):
            session.merge(
                Customer(
                    id=row["id"],
                    name=row["name"],
                    email=row["email"],
                    plan=row["plan"],
                    region=row["region"],
                    created_at=_dt(row["created_at"]),
                )
            )
        for row in _load("subscriptions.json"):
            session.merge(
                Subscription(
                    id=row["id"],
                    customer_id=row["customer_id"],
                    plan=row["plan"],
                    billing_period=row["billing_period"],
                    status=row["status"],
                    monthly_fee_usd=row["monthly_fee_usd"],
                    renews_at=_dt(row["renews_at"]),
                    started_at=_dt(row["started_at"]),
                )
            )
        for row in _load("invoices.json"):
            session.merge(
                Invoice(
                    id=row["id"],
                    customer_id=row["customer_id"],
                    amount_usd=row["amount_usd"],
                    status=row["status"],
                    issued_at=_dt(row["issued_at"]),
                    description=row.get("description") or "",
                    duplicate_of=row.get("duplicate_of"),
                )
            )
        for row in _load("incidents.json"):
            session.merge(
                Incident(
                    id=row["id"],
                    started_at=_dt(row["started_at"]),
                    ended_at=_dt(row["ended_at"]),
                    affected_plans=row["affected_plans"],
                    uptime_pct=row["uptime_pct"],
                    summary=row["summary"],
                )
            )
        if session.query(Usage).count() == 0:
            for row in _load("usage.json"):
                session.add(
                    Usage(
                        customer_id=row["customer_id"],
                        date=row["date"],
                        api_calls=row["api_calls"],
                        errors_by_code=row["errors_by_code"],
                    )
                )
    print("seed complete")


if __name__ == "__main__":
    seed()


def reset_ledger(customer_id: str | None = None) -> int:
    """Delete executed payouts so an eval episode starts from a clean ledger (tau-bench resets DB state
    per task). Never called by the API; evals and tests only."""
    from resolve.db.models import Action

    with get_session() as session:
        q = session.query(Action)
        if customer_id:
            q = q.filter(Action.customer_id == customer_id)
        return q.delete(synchronize_session=False)

"""Northwind Cloud schema. Money never lives on the LLM side of the wall."""

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(200), unique=True)
    plan: Mapped[str] = mapped_column(String(32))
    region: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(DateTime)
    subscriptions: Mapped[list["Subscription"]] = relationship(back_populates="customer")
    invoices: Mapped[list["Invoice"]] = relationship(back_populates="customer")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"))
    plan: Mapped[str] = mapped_column(String(32))
    billing_period: Mapped[str] = mapped_column(String(16))  # monthly | annual
    status: Mapped[str] = mapped_column(String(16))
    monthly_fee_usd: Mapped[float] = mapped_column(Float)
    renews_at: Mapped[datetime] = mapped_column(DateTime)
    started_at: Mapped[datetime] = mapped_column(DateTime)
    customer: Mapped[Customer] = relationship(back_populates="subscriptions")


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"))
    amount_usd: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(16))
    issued_at: Mapped[datetime] = mapped_column(DateTime)
    description: Mapped[str] = mapped_column(String(240), default="")
    duplicate_of: Mapped[str | None] = mapped_column(String(32), nullable=True)
    customer: Mapped[Customer] = relationship(back_populates="invoices")


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime)
    ended_at: Mapped[datetime] = mapped_column(DateTime)
    affected_plans: Mapped[str] = mapped_column(String(120))  # comma-separated
    uptime_pct: Mapped[float] = mapped_column(Float)
    summary: Mapped[str] = mapped_column(Text)


class Usage(Base):
    __tablename__ = "usage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"))
    date: Mapped[str] = mapped_column(String(10))
    api_calls: Mapped[int] = mapped_column(Integer)
    errors_by_code: Mapped[dict[str, Any]] = mapped_column(JSON)


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    customer_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    raw_text: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="running")
    reply: Mapped[str | None] = mapped_column(Text, nullable=True)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
    state_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class Action(Base):
    __tablename__ = "actions"
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_actions_idempotency"),)

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    ticket_id: Mapped[str] = mapped_column(String(32), index=True)
    customer_id: Mapped[str | None] = mapped_column(String(32), index=True, nullable=True)
    target_ref: Mapped[str | None] = mapped_column(String(80), nullable=True)
    type: Mapped[str] = mapped_column(String(32))
    amount_usd: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(16))  # pending | executed | rejected
    idempotency_key: Mapped[str] = mapped_column(String(64), unique=True)
    approved_by: Mapped[str | None] = mapped_column(String(80), nullable=True)
    rule_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    ticket_id: Mapped[str] = mapped_column(String(32), index=True)
    node: Mapped[str] = mapped_column(String(40))
    event: Mapped[str] = mapped_column(String(80))
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    duration_ms: Mapped[float] = mapped_column(Float, default=0.0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)


class RedteamAttempt(Base):
    """Public 'Break the refund' attempts. Text is stored for eval mining; the IP is only kept as a salted hash."""

    __tablename__ = "redteam_attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    ticket_id: Mapped[str] = mapped_column(String(32), index=True)
    text: Mapped[str] = mapped_column(Text)
    outcome: Mapped[str] = mapped_column(String(24))  # breached | human_review | blocked | legit_credit
    stopped_by: Mapped[str] = mapped_column(String(80))
    flags: Mapped[list[str]] = mapped_column(JSON, default=list)
    amount_written_usd: Mapped[float] = mapped_column(Float, default=0.0)
    client_hash: Mapped[str] = mapped_column(String(16), index=True)

"""Regression: idempotency used to be keyed per ticket, so every new ticket about the same duplicate
invoice refunded it again (453 refunds of one $49 duplicate accumulated in dev)."""

from concurrent.futures import ThreadPoolExecutor

from resolve.db.models import Action
from resolve.db.session import get_session
from resolve.graph.runner import approve, run_ticket

DUP = "I was charged twice in October, refund the extra one"


def _refunds(customer_id):
    with get_session() as s:
        return s.query(Action).filter(Action.customer_id == customer_id, Action.type == "refund").all()


def test_second_ticket_for_same_duplicate_is_not_paid():
    first = run_ticket(DUP, "cus_014")
    second = run_ticket("Charged twice!! Refund the duplicate please.", "cus_014")
    assert first["proposed_action"]["amount_usd"] == 49
    assert second["proposed_action"] is None
    rows = _refunds("cus_014")
    assert len(rows) == 1 and rows[0].target_ref == "inv_dup_014_b"


def test_concurrent_tickets_pay_once():
    with ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(lambda _: run_ticket(DUP, "cus_014"), range(6)))
    assert len(_refunds("cus_014")) == 1


def test_two_paused_approvals_for_same_invoice_pay_once():
    a = run_ticket("Refund the $900 professional services double charge immediately", "cus_008")
    b = run_ticket("Please refund the duplicate $900 services charge", "cus_008")
    assert a["status"] == b["status"] == "awaiting_approval"
    approve(a["ticket_id"], "ops", "approve")
    approve(b["ticket_id"], "ops", "approve")
    assert len(_refunds("cus_008")) == 1


def test_same_sla_month_is_credited_once():
    run_ticket("Pro uptime was 99.7% in September. Do I get an SLA credit?", "cus_003")
    again = run_ticket("September uptime credit please, Pro plan.", "cus_003")
    assert again["proposed_action"] is None
    with get_session() as s:
        assert s.query(Action).filter(Action.customer_id == "cus_003", Action.type == "credit").count() == 1

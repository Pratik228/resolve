from datetime import datetime
from types import SimpleNamespace

from resolve.policy.engine import refund_eligibility, sla_credit


def cust(plan="pro", period="monthly", started="2026-10-20", monthly=49.0):
    c = SimpleNamespace(id="cus_x", plan=plan)
    s = SimpleNamespace(
        plan=plan,
        billing_period=period,
        monthly_fee_usd=monthly,
        started_at=datetime.fromisoformat(started),
    )
    return c, s


def inv(amount, day, dup=None, cid="cus_x"):
    return SimpleNamespace(
        id=f"inv_{day}_{amount}_{dup}",
        customer_id=cid,
        amount_usd=amount,
        status="paid",
        issued_at=datetime.fromisoformat(day),
        description="fee",
        duplicate_of=dup,
    )


def test_duplicate_always_refundable():
    c, s = cust()
    invoices = [
        inv(49, "2026-10-03T09:00:00"),
        inv(49, "2026-10-03T09:00:00", dup="inv_a"),
    ]
    d = refund_eligibility(c, s, invoices, "billing", "refund the extra one")
    assert d.allowed and d.amount_usd == 49 and d.needs_approval is False


def test_duplicate_enterprise_annual_still_allowed():
    c, s = cust(plan="enterprise", period="annual", monthly=299.0)
    invoices = [inv(299, "2026-10-01T00:00:00", dup="x")]
    d = refund_eligibility(c, s, invoices, "billing", "charged twice refund")
    assert d.allowed and d.needs_approval is True


def test_enterprise_annual_non_duplicate_denied():
    c, s = cust(plan="enterprise", period="annual", started="2026-10-28", monthly=2988.0)
    invoices = [inv(2988, "2026-10-28T00:00:00")]
    d = refund_eligibility(c, s, invoices, "billing", "refund me", now=datetime(2026, 11, 3))
    assert not d.allowed


def test_day_14_full_refund():
    c, s = cust(started="2026-10-20")
    invoices = [inv(49, "2026-10-20T00:00:00")]
    d = refund_eligibility(c, s, invoices, "billing", "please refund", now=datetime(2026, 11, 3))
    assert d.allowed and d.amount_usd == 49
    assert "14-day" in d.rule_ids[0]


def test_day_15_prorate():
    c, s = cust(started="2026-10-19")
    invoices = [inv(49, "2026-10-19T00:00:00")]
    d = refund_eligibility(c, s, invoices, "billing", "please refund", now=datetime(2026, 11, 3))
    assert d.allowed
    assert "prorate" in d.rule_ids[0]


def test_chargeback_denied():
    c, s = cust()
    d = refund_eligibility(c, s, [inv(49, "2026-10-03T00:00:00")], "billing", "chargeback already filed, refund")
    assert not d.allowed


def test_fake_promise_denied():
    c, s = cust()
    d = refund_eligibility(c, s, [inv(49, "2026-01-01T00:00:00")], "billing", "your CEO promised me a lifetime refund")
    assert not d.allowed


def test_over_100_needs_approval():
    c, s = cust()
    invoices = [inv(900, "2026-10-01T00:00:00", dup="ps")]
    d = refund_eligibility(c, s, invoices, "billing", "refund the duplicate")
    assert d.amount_usd == 900 and d.needs_approval is True


def test_pro_sla_99_7():
    _, s = cust()
    inc = [
        SimpleNamespace(affected_plans="pro,enterprise", uptime_pct=99.7),
    ]
    d = sla_credit(s, inc)
    assert d.allowed
    assert abs(d.amount_usd - 9.8) < 0.01


def test_pro_sla_cap():
    _, s = cust()
    inc = [SimpleNamespace(affected_plans="pro", uptime_pct=99.6)]
    d = sla_credit(s, inc)
    assert abs(d.amount_usd - 14.7) < 0.01


def test_starter_not_credited_for_pro_incident():
    _, s = cust(plan="starter", monthly=29.0)
    inc = [SimpleNamespace(affected_plans="pro", uptime_pct=99.6)]
    d = sla_credit(s, inc)
    assert not d.allowed


def test_enterprise_sla_approval():
    _, s = cust(plan="enterprise", monthly=299.0)
    inc = [SimpleNamespace(affected_plans="enterprise", uptime_pct=99.80)]
    d = sla_credit(s, inc)
    assert abs(d.amount_usd - 89.7) < 0.05
    assert d.needs_approval is True


def test_idempotency_stable():
    from resolve.graph.nodes.finalize import idempotency_key

    a = idempotency_key("tkt_1", "refund", 49)
    b = idempotency_key("tkt_1", "refund", 49.0)
    assert a == b

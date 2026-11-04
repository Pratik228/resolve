from resolve.db.models import Action
from resolve.db.session import get_session
from resolve.graph.runner import run_ticket


def test_finalize_twice_does_not_double_refund():
    text = "I was charged twice in October, refund the extra one"
    state = run_ticket(text, "cus_014", auto_approve=True)
    from resolve.graph.nodes.finalize import finalize_node

    finalize_node(state)
    finalize_node(state)
    with get_session() as session:
        rows = session.query(Action).filter(Action.ticket_id == state["ticket_id"]).all()
    assert len(rows) == 1
    assert rows[0].amount_usd == 49

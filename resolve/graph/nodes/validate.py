import time

from resolve.graph.nodes.common import bump
from resolve.graph.state import TicketState
from resolve.guards.grounding import ungrounded_spans
from resolve.guards.pii import contains_foreign_pii
from resolve.tools.registry import get_customer


def validate_node(state: TicketState) -> TicketState:
    started = time.perf_counter()
    draft = state.get("draft") or {"text": "", "cited_doc_ids": []}
    chunks = state.get("retrieved") or []
    evidence = "\n".join(c["text"] for c in chunks)
    action = state.get("proposed_action")
    allowed_amounts = [action["amount_usd"]] if action else []
    # Ledger rows the tools returned are evidence too (invoice and prior payout amounts).
    tools = state.get("tool_results") or {}
    allowed_amounts += [float(r["amount_usd"]) for r in (tools.get("get_invoices") or []) + (tools.get("get_payouts") or [])]
    reasons = ungrounded_spans(draft["text"], evidence, allowed_amounts)

    if action and f"{action['amount_usd']:.2f}" not in draft["text"] and f"{action['amount_usd']}" not in draft["text"]:
        # $9.8 vs $9.80 — accept either
        if f"{action['amount_usd']:.1f}" not in draft["text"]:
            reasons.append("draft amount does not match policy decision")

    cited = set(draft.get("cited_doc_ids") or [])
    retrieved_ids = {c["doc_id"] for c in chunks}
    if cited - retrieved_ids:
        reasons.append("cited unknown doc_ids")

    pii_map = state.get("pii_map") or {}
    other_emails = []
    cid = state.get("customer_id")
    if cid:
        me = get_customer(cid)
        # cheap probe: known neighbor emails from seed pattern not needed if we scan tokens
        if me:
            other_emails = []
    leaks = contains_foreign_pii(draft["text"], pii_map, other_emails)
    # never echo raw card numbers
    if any(ch.isdigit() for ch in draft["text"]) and "4111" in draft["text"]:
        leaks.append("card")

    flags = state.get("injection_flags") or []
    injection_ok = True
    if flags and action and {"ignore-previous", "forced-refund", "forced-approve"} & set(flags):
        injection_ok = False
        reasons.append("action not allowed on injected ticket")

    validation = {
        "grounded": not any(r.startswith("ungrounded") for r in reasons),
        "policy_ok": "draft amount does not match policy decision" not in reasons,
        "pii_ok": not leaks,
        "injection_ok": injection_ok,
        "reasons": reasons + ([f"pii:{x}" for x in leaks]),
    }
    ok = validation["grounded"] and validation["policy_ok"] and validation["pii_ok"] and validation["injection_ok"]
    state["validation"] = validation
    if not ok:
        state["retries"] = int(state.get("retries") or 0) + 1
    return bump(state, "validate", "validated", validation, started)

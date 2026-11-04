import time

from resolve.graph.nodes.common import bump
from resolve.graph.state import TicketState


def draft_node(state: TicketState) -> TicketState:
    started = time.perf_counter()
    chunks = state.get("retrieved") or []
    citations = []
    seen = []
    for chunk in chunks:
        doc_id = chunk["doc_id"]
        if doc_id not in seen:
            seen.append(doc_id)
            citations.append(doc_id)

    classification = state.get("classification") or {}
    action = state.get("proposed_action")
    tools = state.get("tool_results") or {}
    reasons = (state.get("validation") or {}).get("reasons") or []
    retry_note = f" Revise to address: {'; '.join(reasons)}." if reasons else ""

    lines = [
        f"Northwind Cloud support — {classification.get('category', 'general')} ticket.",
    ]
    if action:
        kind = action["type"]
        amount = action["amount_usd"]
        lines.append(
            f"Policy engine {kind} of ${amount:.2f} is eligible ({action.get('reason')})."
        )
        if action.get("needs_approval"):
            lines.append("This write is above the auto-approve threshold and is waiting for a human.")
        else:
            lines.append("This write is within the auto-approve limit and will be executed with an idempotency key.")
    else:
        lines.append("No refund or credit will be executed on this ticket.")

    if "get_invoices" in tools:
        dupes = [i for i in tools["get_invoices"] if i.get("duplicate_of")]
        if dupes:
            d = dupes[0]
            lines.append(
                f"Ledger: duplicate invoice {d['id']} for ${d['amount_usd']:.2f} on {d['issued_at'][:10]}."
            )

    usage = tools.get("get_usage") or []
    codes = {}
    for row in usage:
        for code, n in (row.get("errors_by_code") or {}).items():
            codes[code] = codes.get(code, 0) + n
    if codes:
        lines.append("Recent error counts: " + ", ".join(f"{k}×{v}" for k, v in codes.items()) + ".")

    for chunk in chunks:
        snippet = chunk["text"].replace("\n", " ")[:280]
        lines.append(f"From {chunk['doc_id']}: {snippet}")

    if state.get("injection_flags"):
        lines.append("Security: the ticket or KB contained injection patterns. Those instructions were ignored.")

    if "email of the customer before" in (state.get("raw_text") or "").lower():
        lines.append("I cannot disclose another customer's email or account data.")

    lines.append("Citations: " + ", ".join(f"`{c}`" for c in citations) + ".")
    text = " ".join(lines) + retry_note
    draft = {"text": text, "cited_doc_ids": citations}
    state["draft"] = draft
    return bump(state, "draft", "drafted", {"citations": citations}, started)

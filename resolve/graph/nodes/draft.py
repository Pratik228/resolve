import re
import time

from resolve.graph.nodes.common import bump
from resolve.graph.state import TicketState
from resolve.llm.provider import get_provider


def kb_sentences(text: str, n: int = 2) -> str:
    """First n plain sentences of a KB chunk: no markdown headings, tables, emphasis or code ticks.
    The template used to paste 280 raw characters, table pipes and all, into customer replies."""
    body = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("|") or line.startswith("<!--"):
            continue
        body.append(line.lstrip("-* ").strip())
    plain = re.sub(r"[*`]", "", " ".join(body))
    sentences = re.split(r"(?<=[.!?])\s+", plain)
    return " ".join(s for s in sentences[:n] if s).strip()


def draft_context(state: TicketState) -> dict:
    """Everything the drafting model may see. Redacted ticket, ledger facts, policy output, KB excerpts.
    Deterministic so it can key a recording."""
    tools = state.get("tool_results") or {}
    action = state.get("proposed_action")
    account = []
    for inv in tools.get("get_invoices") or []:
        if inv.get("duplicate_of"):
            account.append(f"duplicate invoice {inv['id']} for ${inv['amount_usd']:.2f} on {inv['issued_at'][:10]}")
            break
    codes: dict[str, int] = {}
    for row in tools.get("get_usage") or []:
        for code, n in (row.get("errors_by_code") or {}).items():
            codes[code] = codes.get(code, 0) + n
    if codes:
        account.append("recent error counts: " + ", ".join(f"{k} x{v}" for k, v in sorted(codes.items())))
    sub = tools.get("get_subscription")
    if sub:
        account.append(f"plan {sub.get('plan')} ({sub.get('billing_period')})")
    seen, evidence = set(), []
    for c in state.get("retrieved") or []:
        if c["doc_id"] in seen:
            continue
        seen.add(c["doc_id"])
        evidence.append({"doc_id": c["doc_id"], "text": c["text"][:1200]})
    return {
        "ticket": state.get("redacted_text") or "",
        "category": (state.get("classification") or {}).get("category"),
        "decision": (
            {k: action[k] for k in ("type", "amount_usd", "needs_approval", "reason")} if action else None
        ),
        "injection_flags": sorted(state.get("injection_flags") or []),
        "account": account,
        "evidence": evidence,
    }


def draft_node(state: TicketState) -> TicketState:
    started = time.perf_counter()
    provider = get_provider()
    # First attempt only: a model draft that fails validation is replaced by the template, not re-prompted
    # (replay mode would return the same draft anyway).
    if provider is not None and not int(state.get("retries") or 0):
        result = provider.draft(draft_context(state))
        if result is not None:
            out = result.output
            state["draft"] = {"text": out.reply, "cited_doc_ids": out.cited_doc_ids, "model": result.model, "source": result.source}
            state["cost_usd"] = float(state.get("cost_usd") or 0) + result.cost_usd
            return bump(state, "draft", "drafted", {"citations": out.cited_doc_ids, "model": result.model, "source": result.source}, started)
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
        note = state.get("policy_note") or {}
        if any(r.endswith("already-refunded") or r.endswith("already-credited") for r in note.get("rule_ids") or []):
            lines.append(f"{note['reason']}; it will not be paid again.")
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

    quoted = []
    for chunk in chunks:
        if chunk["doc_id"] in quoted or len(quoted) >= 2:
            continue
        snippet = kb_sentences(chunk["text"])
        if snippet:
            quoted.append(chunk["doc_id"])
            lines.append(f"From {chunk.get('title') or chunk['doc_id']}: {snippet}")

    if state.get("injection_flags"):
        lines.append("Security: the ticket or KB contained injection patterns. Those instructions were ignored.")

    if "email of the customer before" in (state.get("raw_text") or "").lower():
        lines.append("I cannot disclose another customer's email or account data.")

    lines.append("Citations: " + ", ".join(f"`{c}`" for c in citations) + ".")
    # Validator reasons stay in state["validation"]; echoing them into the reply leaked the very
    # ungrounded amount being rejected ("Revise to address: ungrounded amount $500.00").
    text = " ".join(lines)
    draft = {"text": text, "cited_doc_ids": citations}
    state["draft"] = draft
    return bump(state, "draft", "drafted", {"citations": citations}, started)

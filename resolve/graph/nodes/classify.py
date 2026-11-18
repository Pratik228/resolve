import re
import time

from resolve.graph.nodes.common import bump
from resolve.graph.state import Classification, TicketState
from resolve.llm.provider import get_provider


ESCALATE = {"legal", "deletion", "contract", "chargeback", "out_of_scope"}


def classify_node(state: TicketState) -> TicketState:
    started = time.perf_counter()
    rules = _rules(state)
    payload = {"rules": rules.model_dump()}
    final = rules
    provider = get_provider()
    if provider is not None:
        result = provider.triage(state.get("redacted_text") or state["raw_text"])
        if result is None:
            payload["llm"] = "miss: rules only"
        else:
            t = result.output
            state["triage"] = {**t.model_dump(), "model": result.model, "source": result.source}
            state["cost_usd"] = float(state.get("cost_usd") or 0) + result.cost_usd
            payload["llm"] = state["triage"]
            category = rules.category
            if rules.category not in ESCALATE:
                # The model may move a ticket *into* escalation, never out of it.
                if t.category in ESCALATE:
                    category = t.category
                elif t.escalate:
                    category = "out_of_scope"  # e.g. another tenant's data: a human owns it
                else:
                    category = t.category
            final = Classification(
                category=category,  # type: ignore[arg-type]
                urgency="high" if category in {"legal", "deletion"} else rules.urgency,
                needs_account_data=True,
                needs_kb=True,
            )
            if t.injection_suspected:
                state["injection_flags"] = list(state.get("injection_flags") or []) + ["llm-injection"]
    state["classification"] = final.model_dump()
    return bump(state, "classify", "classified", {**final.model_dump(), **payload}, started)


def _has(text: str, words: tuple[str, ...]) -> bool:
    """Match at a word start, so plurals still hit. Plain substring matching sent "issue a refund" to legal ("sue")."""
    return any(re.search(rf"(?<![a-z]){re.escape(w)}", text) for w in words)


def _rules(state: TicketState) -> Classification:
    text = (state.get("redacted_text") or state["raw_text"]).lower()
    category = "account"
    if _has(text, ("sue", "lawyer", "ftc", "demand letter", "legal")):
        category = "legal"
    elif "chargeback" in text:
        category = "chargeback"
    elif _has(text, ("delete my account", "gdpr", "erasure", "forgotten")):
        category = "deletion"
    elif _has(text, ("contract", "order-form", "order form", "custom sla")):
        category = "contract"
    elif _has(text, ("uptime", "sla", "incident", "credit me", "outage")):
        category = "sla"
    elif _has(text, ("refund", "charged", "invoice", "billing", "price", "$")):
        category = "billing"
    elif _has(text, ("nw-", "error", "api", "webhook", "sso", "rate")):
        category = "technical"
    urgency = "high" if category in {"legal", "deletion"} else "normal"
    return Classification(
        category=category,  # type: ignore[arg-type]
        urgency=urgency,  # type: ignore[arg-type]
        needs_account_data=True,
        needs_kb=True,
    )

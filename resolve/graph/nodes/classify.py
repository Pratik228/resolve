import time

from resolve.graph.nodes.common import bump
from resolve.graph.state import Classification, TicketState


def classify_node(state: TicketState) -> TicketState:
    started = time.perf_counter()
    text = (state.get("redacted_text") or state["raw_text"]).lower()
    category = "account"
    if any(w in text for w in ("sue", "lawyer", "ftc", "demand letter", "legal")):
        category = "legal"
    elif any(w in text for w in ("delete my account", "gdpr", "erasure", "forgotten")):
        category = "deletion"
    elif any(w in text for w in ("contract", "order-form", "order form", "custom sla")):
        category = "contract"
    elif any(w in text for w in ("uptime", "sla", "incident", "credit me", "outage")):
        category = "sla"
    elif any(w in text for w in ("refund", "charged", "invoice", "billing", "price", "$")):
        category = "billing"
    elif any(w in text for w in ("nw-", "error", "api", "webhook", "sso", "rate")):
        category = "technical"
    urgency = "high" if category in {"legal", "deletion"} else "normal"
    classification = Classification(
        category=category,  # type: ignore[arg-type]
        urgency=urgency,  # type: ignore[arg-type]
        needs_account_data=True,
        needs_kb=True,
    )
    state["classification"] = classification.model_dump()
    return bump(state, "classify", "classified", classification.model_dump(), started)

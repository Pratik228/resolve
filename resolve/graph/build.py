"""LangGraph compile path. The demo runner in runner.py is the source of truth if APIs drift."""

from __future__ import annotations

from typing import Any


def compile_graph() -> Any:
    try:
        from langgraph.graph import END, START, StateGraph

        from resolve.graph.nodes.approval import approval_node
        from resolve.graph.nodes.classify import classify_node
        from resolve.graph.nodes.draft import draft_node
        from resolve.graph.nodes.finalize import escalate_node, finalize_node
        from resolve.graph.nodes.injection_scan import injection_scan_node
        from resolve.graph.nodes.plan import plan_node
        from resolve.graph.nodes.policy_gate import policy_gate_node
        from resolve.graph.nodes.redact import redact_node
        from resolve.graph.nodes.retrieve import retrieve_node
        from resolve.graph.nodes.tools_node import tools_node
        from resolve.graph.nodes.validate import validate_node
        from resolve.graph.state import TicketState
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(f"LangGraph is not available: {exc}") from exc

    graph = StateGraph(dict)

    graph.add_node("redact", redact_node)
    graph.add_node("injection_scan", injection_scan_node)
    graph.add_node("classify", classify_node)
    graph.add_node("plan", plan_node)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("tools", tools_node)
    graph.add_node("policy_gate", policy_gate_node)
    graph.add_node("draft", draft_node)
    graph.add_node("validate", validate_node)
    graph.add_node("approval", approval_node)
    graph.add_node("finalize", finalize_node)
    graph.add_node("escalate", escalate_node)

    graph.add_edge(START, "redact")
    graph.add_edge("redact", "injection_scan")
    graph.add_edge("injection_scan", "classify")

    def after_classify(state: TicketState) -> str:
        cat = (state.get("classification") or {}).get("category")
        if cat in {"legal", "deletion", "contract"}:
            return "escalate"
        return "plan"

    graph.add_conditional_edges("classify", after_classify, {"escalate": "escalate", "plan": "plan"})
    graph.add_edge("plan", "retrieve")
    graph.add_edge("plan", "tools")
    graph.add_edge("retrieve", "policy_gate")
    graph.add_edge("tools", "policy_gate")
    graph.add_edge("policy_gate", "draft")
    graph.add_edge("draft", "validate")

    def after_validate(state: TicketState) -> str:
        v = state.get("validation") or {}
        ok = v.get("grounded") and v.get("policy_ok") and v.get("pii_ok") and v.get("injection_ok")
        if not ok and int(state.get("retries") or 0) < 2:
            return "draft"
        if not ok:
            return "escalate"
        action = state.get("proposed_action")
        if action and action.get("needs_approval"):
            return "approval"
        return "finalize"

    graph.add_conditional_edges(
        "validate",
        after_validate,
        {"draft": "draft", "escalate": "escalate", "approval": "approval", "finalize": "finalize"},
    )

    def after_approval(state: TicketState) -> str:
        if state.get("status") == "escalated":
            return "escalate"
        if state.get("status") == "awaiting_approval":
            return END
        return "finalize"

    graph.add_conditional_edges(
        "approval", after_approval, {"escalate": "escalate", "finalize": "finalize", END: END}
    )
    graph.add_edge("finalize", END)
    graph.add_edge("escalate", END)
    return graph.compile()

"""OpenTelemetry traces for each ticket, named per the GenAI semantic conventions (development status, pinned 1.29).

One trace per ticket: an ``invoke_agent resolve`` root span and one child span per graph node. Model calls are
``chat <model>`` spans with ``gen_ai.*`` attributes; account lookups are ``execute_tool <name>`` spans. Money
decisions carry ``resolve.decision.*`` so a trace answers "who decided this amount, and how long did it take".

OTEL_EXPORTER=off (default) | console | otlp. otlp posts to OTEL_EXPORTER_OTLP_ENDPOINT (default
http://127.0.0.1:4318, e.g. the Jaeger service in docker-compose.yml). With the SDK not installed, or off,
every call here is a no-op, so the default path and CI pay nothing.
"""
from __future__ import annotations

import contextvars
import os
import time
from typing import Any

_tracer = None
_ready = False
_root: contextvars.ContextVar = contextvars.ContextVar("resolve_root_span", default=None)

# The graph node that owns each step: code, model or person. Mirrors the trace page colours.
OWNER = {"classify": "model", "draft": "model", "approval": "person"}


def _init():
    global _tracer, _ready
    _ready = True
    mode = os.environ.get("OTEL_EXPORTER", "off").strip().lower()
    if mode == "off":
        return
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter, SimpleSpanProcessor
    except ImportError:
        return
    provider = TracerProvider(resource=Resource.create({"service.name": "resolve", "service.version": "0.2"}))
    if mode == "console":
        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    else:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

        endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://127.0.0.1:4318").rstrip("/")
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{endpoint}/v1/traces")))
    trace.set_tracer_provider(provider)
    _tracer = trace.get_tracer("resolve.graph")


def tracer():
    if not _ready:
        _init()
    return _tracer


class ticket_span:
    """Root span for one ticket run (or resume after approval)."""

    def __init__(self, state: dict, operation: str = "invoke_agent"):
        self.state, self.operation, self.span, self.token = state, operation, None, None

    def __enter__(self):
        t = tracer()
        if t is None:
            return self
        self.span = t.start_span(
            f"{self.operation} resolve",
            attributes={
                "gen_ai.operation.name": self.operation,
                "gen_ai.agent.name": "resolve",
                "gen_ai.conversation.id": self.state.get("ticket_id") or "",
                "resolve.customer_id": self.state.get("customer_id") or "",
            },
        )
        self.token = _root.set(self.span)
        return self

    def __exit__(self, *exc):
        if self.span is None:
            return False
        s = self.state
        action = s.get("proposed_action") or {}
        self.span.set_attribute("resolve.status", s.get("status") or "")
        self.span.set_attribute("resolve.steps", int(s.get("step_count") or 0))
        self.span.set_attribute("resolve.cost_usd", float(s.get("cost_usd") or 0))
        if action:
            self.span.set_attribute("resolve.decision.type", action.get("type") or "")
            self.span.set_attribute("resolve.decision.amount_usd", float(action.get("amount_usd") or 0))
            self.span.set_attribute("resolve.decision.needs_approval", bool(action.get("needs_approval")))
        self.span.end()
        _root.reset(self.token)
        return False


def node_span(node: str, event: str, payload: dict[str, Any], duration_ms: float, state: dict) -> None:
    """Record a finished node as a child span, back-dated to its measured start."""
    t = tracer()
    root = _root.get()
    if t is None or root is None:
        return
    from opentelemetry import trace

    end_ns = time.time_ns()
    start_ns = end_ns - int(duration_ms * 1e6)
    attrs: dict[str, Any] = {"resolve.node": node, "resolve.event": event, "resolve.owner": OWNER.get(node, "code")}
    name = node
    llm = payload.get("llm") if isinstance(payload.get("llm"), dict) else None
    if node == "classify" and llm:
        name = f"chat {llm.get('model', 'claude')}"
        attrs |= {"gen_ai.operation.name": "chat", "gen_ai.provider.name": "anthropic",
                  "gen_ai.request.model": str(llm.get("model", "")), "resolve.llm.source": str(llm.get("source", ""))}
    elif node == "draft" and payload.get("source") in {"replay", "live"}:
        name = f"chat {payload.get('model', 'claude')}"
        attrs |= {"gen_ai.operation.name": "chat", "gen_ai.provider.name": "anthropic",
                  "gen_ai.request.model": str(payload.get("model", "")), "resolve.llm.source": payload["source"]}
    elif node == "tools":
        name = "execute_tool account_lookup"
        attrs |= {"gen_ai.operation.name": "execute_tool",
                  "gen_ai.tool.name": ",".join(state.get("plan") or [])}
    elif node == "policy_gate":
        action = state.get("proposed_action") or {}
        attrs |= {"resolve.decision.type": action.get("type") or "none",
                  "resolve.decision.amount_usd": float(action.get("amount_usd") or 0)}
    span = t.start_span(name, context=trace.set_span_in_context(root), start_time=start_ns, attributes=attrs)
    span.end(end_time=end_ns)

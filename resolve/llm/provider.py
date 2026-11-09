"""LLM providers.

- ``off``    no model; deterministic rules only (CI default).
- ``replay`` serve recorded model outputs from evals/recordings/*.jsonl; a miss returns None and
             the graph falls back to rules. $0, deterministic, used by the public demo.
- ``live``   call Claude through the Anthropic SDK with structured outputs, under a hard spend cap.
             Set RECORD_LLM=1 to append every live output to the recordings.

Recordings are keyed by sha256(kind, PROMPT_VERSION, model-visible input) so a prompt or input change is a miss,
never a stale hit.
"""

from __future__ import annotations

import hashlib
import json
import threading
from pathlib import Path
from typing import Any

from resolve.config import get_settings
from resolve.llm.prompts import DRAFT_SYSTEM, PROMPT_VERSION, TRIAGE_SYSTEM
from resolve.llm.schemas import DraftOut, Triage

# $ per 1M tokens (input, output). Source: Anthropic pricing, cached 2026-10-06.
PRICES = {"claude-opus-5-5": (4.0, 20.0), "claude-sonnet-5-5": (2.0, 10.0), "claude-haiku-5-5": (0.10, 0.50)}


def record_key(kind: str, payload: Any) -> str:
    raw = json.dumps({"kind": kind, "v": PROMPT_VERSION, "input": payload}, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def _recordings_path(kind: str) -> Path:
    return get_settings().evals_dir / "recordings" / f"{kind}_{PROMPT_VERSION}.jsonl"


class Result:
    def __init__(self, output: Any, model: str, cost_usd: float, source: str):
        self.output, self.model, self.cost_usd, self.source = output, model, cost_usd, source


class ReplayProvider:
    def __init__(self) -> None:
        self._cache: dict[str, dict[str, dict]] = {}

    def _load(self, kind: str) -> dict[str, dict]:
        if kind not in self._cache:
            path = _recordings_path(kind)
            rows = {}
            if path.exists():
                for line in path.read_text().splitlines():
                    if line.strip():
                        r = json.loads(line)
                        rows[r["key"]] = r
            self._cache[kind] = rows
        return self._cache[kind]

    def _get(self, kind: str, payload: Any, model_cls):
        row = self._load(kind).get(record_key(kind, payload))
        if not row:
            return None
        return Result(model_cls.model_validate(row["output"]), row.get("model", "?"), 0.0, "replay")

    def triage(self, ticket: str) -> Result | None:
        return self._get("triage", {"ticket": ticket}, Triage)

    def draft(self, context: dict) -> Result | None:
        return self._get("draft", context, DraftOut)


class LiveProvider(ReplayProvider):
    """Replay first (free), then Claude. Spend is capped per process by DEMO_SPEND_CAP_USD."""

    _lock = threading.Lock()
    spent_usd = 0.0

    def __init__(self) -> None:
        super().__init__()
        import anthropic

        self._client = anthropic.Anthropic(api_key=get_settings().anthropic_api_key or None)
        self.model = get_settings().llm_model

    def _call(self, kind: str, system: str, payload: Any, model_cls, max_tokens: int):
        hit = self._get(kind, payload, model_cls)
        if hit:
            return hit
        settings = get_settings()
        if LiveProvider.spent_usd >= settings.demo_spend_cap_usd:
            return None  # cap reached: degrade to rules, never to an unbounded bill
        import anthropic

        try:
            resp = self._client.messages.parse(
                model=self.model,
                max_tokens=max_tokens,
                system=system,
                output_config={"effort": "low"},
                messages=[{"role": "user", "content": json.dumps(payload)}],
                output_format=model_cls,
            )
        except (anthropic.APIStatusError, anthropic.APIConnectionError):
            return None
        if resp.stop_reason == "refusal" or resp.parsed_output is None:
            return None
        pin, pout = PRICES.get(self.model, (4.0, 20.0))
        cost = resp.usage.input_tokens * pin / 1e6 + resp.usage.output_tokens * pout / 1e6
        with LiveProvider._lock:
            LiveProvider.spent_usd += cost
        if settings.record_llm:
            row = {"key": record_key(kind, payload), "kind": kind, "model": self.model,
                   "input": payload, "output": resp.parsed_output.model_dump()}
            with _recordings_path(kind).open("a") as f:
                f.write(json.dumps(row) + "\n")
        return Result(resp.parsed_output, self.model, cost, "live")

    def triage(self, ticket: str) -> Result | None:
        return self._call("triage", TRIAGE_SYSTEM, {"ticket": ticket}, Triage, 1024)

    def draft(self, context: dict) -> Result | None:
        return self._call("draft", DRAFT_SYSTEM, context, DraftOut, 2048)


_PROVIDER = None


def get_provider():
    """None when RESOLVE_LLM=off."""
    global _PROVIDER
    mode = get_settings().resolve_llm.strip().lower()
    if mode == "off":
        return None
    if _PROVIDER is None or getattr(_PROVIDER, "_mode", None) != mode:
        _PROVIDER = LiveProvider() if mode == "live" else ReplayProvider()
        _PROVIDER._mode = mode
    return _PROVIDER

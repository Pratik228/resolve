"""Golden-output snapshot for RESOLVE_LLM=off. Regenerate only with `make snapshot`."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from evals.harness import ensure_data, load_golden
from resolve.db.seed import reset_ledger
from evals.meta import build_meta
from resolve.config import get_settings
from resolve.graph.runner import run_ticket

SNAPSHOT = get_settings().evals_dir / "snapshots" / "deterministic_v1.json"


def _action(raw: dict | None) -> dict | None:
    if not raw:
        return None
    return {
        "type": raw.get("type"),
        "amount_usd": round(float(raw["amount_usd"]), 2) if raw.get("amount_usd") is not None else None,
        "needs_approval": bool(raw.get("needs_approval")),
        "rule_ids": list(raw.get("rule_ids") or []),
    }


def record_from_state(case_id: str, state: dict) -> dict:
    draft = state.get("draft") or {}
    text = state.get("reply") or draft.get("text") or ""
    return {
        "id": case_id,
        "tools_called": list(state.get("plan") or []),
        "action": _action(state.get("proposed_action")),
        "status": state.get("status"),
        "cited_doc_ids": list(draft.get("cited_doc_ids") or []),
        "reply_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
    }


def run_all(auto_approve: bool = False) -> list[dict]:
    os.environ["RESOLVE_LLM"] = "off"
    get_settings.cache_clear()
    ensure_data()
    rows = []
    for case in load_golden():
        reset_ledger(case.get("customer_id"))
        state = run_ticket(case["ticket"], case.get("customer_id"), auto_approve=auto_approve)
        rows.append(record_from_state(case["id"], state))
    return rows


def write_snapshot() -> Path:
    rows = run_all()
    payload = {
        "meta": build_meta(n=len(rows), retrieval_config="snapshot"),
        "auto_approve": False,
        "cases": rows,
    }
    SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"wrote {SNAPSHOT} ({len(rows)} cases)")
    return SNAPSHOT


def load_snapshot() -> dict:
    return json.loads(SNAPSHOT.read_text())


def diff_snapshots(expected: list[dict], actual: list[dict]) -> list[dict]:
    exp = {c["id"]: c for c in expected}
    got = {c["id"]: c for c in actual}
    diffs = []
    for cid in sorted(set(exp) | set(got)):
        if cid not in exp:
            diffs.append({"id": cid, "error": "unexpected case"})
            continue
        if cid not in got:
            diffs.append({"id": cid, "error": "missing case"})
            continue
        if exp[cid] != got[cid]:
            diffs.append({"id": cid, "expected": exp[cid], "actual": got[cid]})
    return diffs


if __name__ == "__main__":
    write_snapshot()

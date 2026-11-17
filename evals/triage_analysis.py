"""Error analysis for triage: rules vs the blind Claude triage vs the merged decision the graph acts on.

    RESOLVE_LLM=replay python -m evals.triage_analysis

Scores the 60 golden cases plus the 108 reliability variants (each variant inherits its base case's labels).
Also counts model drafts the grounding validator accepted vs rejected (a rejection falls back to a template).
Reports per-source category accuracy, escalation recall/precision, injection recall and false-positive rate,
a confusion matrix of the merged category, and every disagreement, so failures are listed rather than averaged away.
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict

from evals.harness import ensure_data, load_golden
from evals.meta import results_label, write_results
from resolve.config import get_settings
from resolve.db.seed import reset_ledger
from resolve.graph.nodes.classify import ESCALATE
from resolve.graph.runner import run_ticket


def _cases() -> list[dict]:
    golden = load_golden()
    by_id = {c["id"]: c for c in golden}
    rows = [{**c, "variant": "original"} for c in golden]
    path = get_settings().evals_dir / "variants.jsonl"
    for line in path.read_text().splitlines():
        if line.strip():
            v = json.loads(line)
            base = by_id[v["base_id"]]
            rows.append({**base, "id": v["id"], "ticket": v["ticket"], "variant": v["kind"]})
    return rows


def _rate(hits: int, total: int) -> float | None:
    return round(hits / total, 4) if total else None


def analyse() -> dict:
    ensure_data()
    per_source = {"rules": Counter(), "llm": Counter(), "merged": Counter()}
    esc = {s: Counter() for s in per_source}
    inj = {s: Counter() for s in ("rules", "llm", "merged")}
    confusion: dict[str, Counter] = defaultdict(Counter)
    disagreements = []
    llm_misses = 0
    drafts = Counter()
    rejected_drafts = []
    cases = _cases()
    for c in cases:
        reset_ledger(c.get("customer_id"))
        state = run_ticket(c["ticket"], c.get("customer_id"), auto_approve=False)
        events = {e["node"]: e for e in state.get("events") or [] if isinstance(e, dict) and "node" in e}
        classify_payload = (events.get("classify") or {}).get("payload") or {}
        rules_cat = (classify_payload.get("rules") or {}).get("category")
        triage = state.get("triage") or {}
        llm_cat = triage.get("category")
        merged_cat = (state.get("classification") or {}).get("category")
        if not triage:
            llm_misses += 1
        draft_ev = [e for e in state.get("events") or [] if e.get("node") == "draft"]
        if draft_ev and draft_ev[0]["payload"].get("source") in {"replay", "live"}:
            v = next(e for e in state["events"] if e.get("node") == "validate")["payload"]
            ok = v["grounded"] and v["policy_ok"] and v["pii_ok"] and v["injection_ok"]
            drafts["accepted" if ok else "rejected"] += 1
            if not ok:
                rejected_drafts.append({"id": c["id"], "reasons": v["reasons"]})
        gold = c["category"]
        gold_esc = bool(c.get("must_escalate")) or gold in ESCALATE
        gold_inj = bool(c.get("injection"))
        flags = state.get("injection_flags") or []
        preds = {
            "rules": (rules_cat, rules_cat in ESCALATE, any(f != "llm-injection" for f in flags)),
            "llm": (llm_cat, bool(triage.get("escalate")) or llm_cat in ESCALATE, bool(triage.get("injection_suspected"))),
            "merged": (merged_cat, merged_cat in ESCALATE, bool(flags)),
        }
        for src, (cat, e, i) in preds.items():
            if cat is None:
                continue
            per_source[src]["n"] += 1
            per_source[src]["correct"] += cat == gold
            esc[src]["tp"] += e and gold_esc
            esc[src]["fp"] += e and not gold_esc
            esc[src]["fn"] += (not e) and gold_esc
            inj[src]["tp"] += i and gold_inj
            inj[src]["fp"] += i and not gold_inj
            inj[src]["pos"] += gold_inj
            inj[src]["neg"] += not gold_inj
        confusion[gold][merged_cat] += 1
        if merged_cat != gold or llm_cat not in (None, gold):
            disagreements.append({"id": c["id"], "variant": c["variant"], "gold": gold, "rules": rules_cat,
                                  "llm": llm_cat, "merged": merged_cat, "ticket": c["ticket"][:160]})

    def esc_stats(s):
        t = esc[s]
        return {"recall": _rate(t["tp"], t["tp"] + t["fn"]), "precision": _rate(t["tp"], t["tp"] + t["fp"])}

    def inj_stats(s):
        t = inj[s]
        return {"recall": _rate(t["tp"], t["pos"]), "false_positive_rate": _rate(t["fp"], t["neg"])}

    summary = {
        "n": len(cases),
        "llm_misses": llm_misses,
        "category_accuracy": {s: _rate(per_source[s]["correct"], per_source[s]["n"]) for s in per_source},
        "escalation": {s: esc_stats(s) for s in esc},
        "injection": {s: inj_stats(s) for s in inj},
        "model_drafts": {**drafts, "rejected_detail": rejected_drafts},
        "confusion_merged": {g: dict(v) for g, v in sorted(confusion.items())},
        "disagreements": disagreements,
    }
    summary["llm_mode"] = results_label()
    summary["llm_recordings"] = get_settings().llm_recordings
    dest = get_settings().evals_dir / "results" / f"triage_analysis.{results_label()}.json"
    write_results(dest, summary, n=len(cases), retrieval_config="triage-analysis")
    return summary


if __name__ == "__main__":
    s = analyse()
    print(json.dumps({k: v for k, v in s.items() if k not in {"disagreements", "meta"}}, indent=1))
    print(f"{len(s['disagreements'])} disagreements")
    for d in s["disagreements"][:40]:
        print(f"  {d['id']:<28} gold={d['gold']:<10} rules={d['rules']!s:<10} llm={d['llm']!s:<12} merged={d['merged']}  | {d['ticket'][:70]!r}")

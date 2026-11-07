"""Retrieval ablation. Numbers are measured on this machine's golden set — never invented."""

from __future__ import annotations

import json
import statistics
import time

from evals.meta import write_results
from resolve.config import get_settings
from resolve.retrieval.ingest import load_index
from resolve.retrieval.rerank import rerank
from resolve.retrieval.rewrite import rewrite


def load_golden() -> list[dict]:
    path = get_settings().evals_dir / "golden.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def recall_at_k(expected: list[str], retrieved: list[str], k: int = 4) -> float:
    if not expected:
        return 1.0
    got = set(retrieved[:k])
    return len(got & set(expected)) / len(set(expected))


def mrr(expected: list[str], retrieved: list[str]) -> float:
    for i, doc in enumerate(retrieved, start=1):
        if doc in expected:
            return 1.0 / i
    return 0.0


def _docs(hits: list[dict]) -> list[str]:
    docs: list[str] = []
    for h in hits:
        if h["doc_id"] not in docs:
            docs.append(h["doc_id"])
    return docs


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    return float(statistics.quantiles(values, n=100, method="inclusive")[p - 1])


def _search(index, ticket: str, search_mode: str, rewrite_mode: str, do_rerank: bool) -> list[dict]:
    rewritten = rewrite(ticket, rewrite_mode)
    k = 20 if do_rerank else 4
    hits = index.search_multi(rewritten.queries, k=k, mode=search_mode, filter_query=ticket)
    if do_rerank:
        hits = rerank(ticket, hits, top_n=4)
    return hits


def run() -> dict:
    index = load_index()
    cases = load_golden()
    configs = [
        ("dense", "dense", "off", False),
        ("bm25", "bm25", "off", False),
        ("hybrid", "hybrid", "off", False),
        ("hybrid+rerank", "hybrid", "off", True),
        ("hybrid+rewrite_rules", "hybrid", "rules", False),
        ("hybrid+rewrite_llm", "hybrid", "llm", False),
        ("hybrid+rewrite_rules+rerank", "hybrid", "rules", True),
    ]
    table = []
    for name, search_mode, rewrite_mode, do_rerank in configs:
        recs = []
        mrrs = []
        latencies = []
        for case in cases:
            t0 = time.perf_counter()
            hits = _search(index, case["ticket"], search_mode, rewrite_mode, do_rerank)
            latencies.append((time.perf_counter() - t0) * 1000)
            docs = _docs(hits)
            recs.append(recall_at_k(case.get("expected_doc_ids") or [], docs, 4))
            mrrs.append(mrr(case.get("expected_doc_ids") or [], docs))
        row = {
            "config": name,
            "rewrite": rewrite_mode,
            "recall_at_4": round(sum(recs) / len(recs), 4),
            "mrr": round(sum(mrrs) / len(mrrs), 4),
            "p50_ms": round(_percentile(latencies, 50), 2),
            "p95_ms": round(_percentile(latencies, 95), 2),
            "p95_ms_per_query": round(_percentile(latencies, 95), 2),
            "n": len(cases),
            "cost_usd_per_ticket": 0.0,
        }
        table.append(row)

    baseline = next(r for r in table if r["config"] == "hybrid")
    rules = next(r for r in table if r["config"] == "hybrid+rewrite_rules")
    keep_rules = (rules["recall_at_4"], rules["mrr"]) > (baseline["recall_at_4"], baseline["mrr"])
    decision = {
        "keep_query_rewrite_rules": keep_rules,
        "reason": (
            "rules wins on (Recall@4, MRR) vs hybrid"
            if keep_rules
            else "rules does not beat hybrid; QUERY_REWRITE stays off"
        ),
        "hybrid_recall_at_4": baseline["recall_at_4"],
        "rules_recall_at_4": rules["recall_at_4"],
        "hybrid_mrr": baseline["mrr"],
        "rules_mrr": rules["mrr"],
    }

    dest = get_settings().evals_dir / "results" / "ablation.json"
    write_results(
        dest,
        {"rows": table, "query_rewrite_decision": decision},
        n=len(cases),
        retrieval_config=",".join(c[0] for c in configs),
    )
    print("| config | rewrite | Recall@4 | MRR | p50 ms | p95 ms |")
    print("|---|---|---|---|---|---|")
    for row in table:
        print(
            f"| {row['config']} | {row['rewrite']} | {row['recall_at_4']} | "
            f"{row['mrr']} | {row['p50_ms']} | {row['p95_ms']} |"
        )
    print("decision:", decision)
    return {"rows": table, "query_rewrite_decision": decision}


if __name__ == "__main__":
    from resolve.db.seed import seed
    from resolve.retrieval.ingest import ingest

    seed()
    ingest()
    run()

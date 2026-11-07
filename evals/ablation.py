"""Retrieval ablation. Numbers are measured on this machine's golden set — never invented."""

from __future__ import annotations

import hashlib
import json
import statistics
import time

from evals.meta import write_results
from resolve.config import get_settings
from resolve.retrieval.hybrid import HybridIndex
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


def split_of(case_id: str) -> str:
    """Stable 50/50 dev/test split. Configs are *chosen* on dev and *reported* on test."""
    return "dev" if int(hashlib.sha256(case_id.encode()).hexdigest(), 16) % 2 == 0 else "test"


# name, embedder, mode, bm25_weight, rewrite, reranker
CONFIGS = [
    ("bm25", "hash-384", "bm25", 1.0, "off", "identity"),
    ("dense:hash", "hash-384", "dense", 1.0, "off", "identity"),
    ("dense:bge", "bge-small", "dense", 1.0, "off", "identity"),
    ("hybrid:hash 2:1", "hash-384", "hybrid", 2.0, "off", "identity"),
    ("hybrid:bge 1:1", "bge-small", "hybrid", 1.0, "off", "identity"),
    ("hybrid:bge 2:1", "bge-small", "hybrid", 2.0, "off", "identity"),
    ("hybrid:bge 2:1 +rewrite", "bge-small", "hybrid", 2.0, "rules", "identity"),
    ("hybrid:bge 2:1 +rerank", "bge-small", "hybrid", 2.0, "off", "minilm"),
    ("hybrid:bge 2:1 +rewrite +rerank", "bge-small", "hybrid", 2.0, "rules", "minilm"),
    ("hybrid:hash 2:1 +rewrite", "hash-384", "hybrid", 2.0, "rules", "identity"),
]


def _search(index, ticket: str, search_mode: str, rewrite_mode: str, reranker: str) -> list[dict]:
    rewritten = rewrite(ticket, rewrite_mode)
    k = 20 if reranker != "identity" else 4
    hits = index.search_multi(rewritten.queries, k=k, mode=search_mode, filter_query=ticket)
    if reranker != "identity":
        hits = rerank(ticket, hits, top_n=4, reranker=reranker)
    return hits


def _score(cases: list[dict], results: dict[str, list[str]]) -> tuple[float, float]:
    if not cases:
        return 0.0, 0.0
    rec = [recall_at_k(c.get("expected_doc_ids") or [], results[c["id"]], 4) for c in cases]
    rr = [mrr(c.get("expected_doc_ids") or [], results[c["id"]]) for c in cases]
    return round(sum(rec) / len(rec), 4), round(sum(rr) / len(rr), 4)


def run() -> dict:
    base = load_index()
    chunks = list(base.chunks.values())
    cases = load_golden()
    dev = [c for c in cases if split_of(c["id"]) == "dev"]
    test = [c for c in cases if split_of(c["id"]) == "test"]
    indexes: dict[tuple[str, float], HybridIndex] = {}
    table = []
    for name, embedder, mode, weight, rewrite_mode, reranker in CONFIGS:
        index = indexes.setdefault((embedder, weight), HybridIndex(chunks, embedder, weight))
        _search(index, "warm-up query", mode, rewrite_mode, reranker)  # load models outside timing
        if hasattr(index.embedder, "_qcache"):
            index.embedder._qcache.clear()  # no cross-config cache hits in the latency columns
        results: dict[str, list[str]] = {}
        latencies = []
        for case in cases:
            t0 = time.perf_counter()
            hits = _search(index, case["ticket"], mode, rewrite_mode, reranker)
            latencies.append((time.perf_counter() - t0) * 1000)
            results[case["id"]] = _docs(hits)
        r_all, m_all = _score(cases, results)
        r_dev, m_dev = _score(dev, results)
        r_test, m_test = _score(test, results)
        table.append(
            {
                "config": name,
                "embedding": embedder,
                "mode": mode,
                "bm25_weight": weight,
                "rewrite": rewrite_mode,
                "reranker": reranker,
                "recall_at_4": r_all,
                "mrr": m_all,
                "dev_recall_at_4": r_dev,
                "dev_mrr": m_dev,
                "test_recall_at_4": r_test,
                "test_mrr": m_test,
                "p50_ms": round(_percentile(latencies, 50), 2),
                "p95_ms": round(_percentile(latencies, 95), 2),
                "n": len(cases),
                "cost_usd_per_ticket": 0.0,
            }
        )

    # Selection uses dev only; ties go to the cheaper (lower p95) config.
    chosen = max(table, key=lambda r: (r["dev_recall_at_4"], r["dev_mrr"], -r["p95_ms"]))
    baseline = next(r for r in table if r["config"] == "hybrid:hash 2:1")
    decision = {
        "chosen_config": chosen["config"],
        "selected_on": f"dev (n={len(dev)})",
        "reported_on": f"test (n={len(test)})",
        "chosen_test_recall_at_4": chosen["test_recall_at_4"],
        "chosen_test_mrr": chosen["test_mrr"],
        "baseline_config": baseline["config"],
        "baseline_test_recall_at_4": baseline["test_recall_at_4"],
        "baseline_test_mrr": baseline["test_mrr"],
    }

    dest = get_settings().evals_dir / "results" / "ablation.json"
    write_results(
        dest,
        {"rows": table, "decision": decision},
        n=len(cases),
        retrieval_config=",".join(c[0] for c in CONFIGS),
    )
    print("| config | R@4 dev | R@4 test | MRR test | R@4 all | p95 ms |")
    print("|---|---|---|---|---|---|")
    for row in table:
        print(
            f"| {row['config']} | {row['dev_recall_at_4']} | {row['test_recall_at_4']} | "
            f"{row['test_mrr']} | {row['recall_at_4']} | {row['p95_ms']} |"
        )
    print("decision:", decision)
    return {"rows": table, "decision": decision}


if __name__ == "__main__":
    from resolve.db.seed import seed
    from resolve.retrieval.ingest import ingest

    seed()
    ingest()
    run()

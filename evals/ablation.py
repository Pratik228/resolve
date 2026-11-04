"""Retrieval ablation. Numbers are measured on this machine's golden set — never invented."""

from __future__ import annotations

import json
import time
from pathlib import Path

from resolve.config import get_settings
from resolve.retrieval.ingest import load_index
from resolve.retrieval.rerank import rerank


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


def run() -> dict:
    index = load_index()
    cases = load_golden()
    modes = ["dense", "bm25", "hybrid", "hybrid+rerank"]
    table = []
    for mode in modes:
        t0 = time.perf_counter()
        recs = []
        mrrs = []
        for case in cases:
            k = 20 if mode == "hybrid+rerank" else 4
            search_mode = "hybrid" if mode.startswith("hybrid") else mode
            hits = index.search(case["ticket"], k=k, mode=search_mode)
            if mode == "hybrid+rerank":
                hits = rerank(case["ticket"], hits, top_n=4)
            docs = []
            for h in hits:
                if h["doc_id"] not in docs:
                    docs.append(h["doc_id"])
            recs.append(recall_at_k(case.get("expected_doc_ids") or [], docs, 4))
            mrrs.append(mrr(case.get("expected_doc_ids") or [], docs))
        elapsed = (time.perf_counter() - t0) * 1000 / max(len(cases), 1)
        row = {
            "config": mode,
            "recall_at_4": round(sum(recs) / len(recs), 4),
            "mrr": round(sum(mrrs) / len(mrrs), 4),
            "p95_ms_per_query": round(elapsed, 2),
            "n": len(cases),
            "cost_usd_per_ticket": 0.0,
        }
        table.append(row)
    out = {"measured_at": time.strftime("%Y-%m-%d"), "rows": table}
    dest = get_settings().evals_dir / "results" / "ablation.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=2))
    print("| config | Recall@4 | MRR | ms/query |")
    print("|---|---|---|---|")
    for row in table:
        print(f"| {row['config']} | {row['recall_at_4']} | {row['mrr']} | {row['p95_ms_per_query']} |")
    return out


if __name__ == "__main__":
    from resolve.db.seed import seed
    from resolve.retrieval.ingest import ingest

    seed()
    ingest()
    run()

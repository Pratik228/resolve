import pytest

from evals.ablation import recall_at_k
from evals.harness import ensure_data, load_golden
from resolve.retrieval.ingest import load_index


@pytest.fixture(scope="session", autouse=True)
def _data():
    ensure_data()


@pytest.mark.fast
def test_fast_mean_recall():
    index = load_index()
    cases = load_golden()[:25]
    scores = []
    for case in cases:
        hits = index.search(case["ticket"], k=12, mode="hybrid")
        docs = []
        for h in hits:
            if h["doc_id"] not in docs:
                docs.append(h["doc_id"])
        expected = case.get("expected_doc_ids") or []
        scores.append(recall_at_k(expected, docs, 4))
    assert sum(scores) / len(scores) >= 0.5


@pytest.mark.eval
def test_error_code_exact_hit():
    index = load_index()
    hits = index.search("daily cap code NW-4031 please", k=8, mode="hybrid")
    docs = [h["doc_id"] for h in hits]
    assert "NW-4031" in docs[:4]

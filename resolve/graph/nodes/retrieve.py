import time

from resolve.config import get_settings
from resolve.graph.nodes.common import bump
from resolve.graph.state import TicketState
from resolve.retrieval.ingest import load_index
from resolve.retrieval.rerank import rerank


def retrieve_node(state: TicketState) -> TicketState:
    started = time.perf_counter()
    settings = get_settings()
    query = state.get("redacted_text") or state["raw_text"]
    index = load_index()
    hits = index.search(query, k=settings.retrieve_k, mode="hybrid")
    top = rerank(query, hits, top_n=settings.rerank_top_n)
    # Never let archived docs through even if the filter slipped
    top = [h for h in top if h.get("status") == "active"]
    state["retrieved"] = top
    return bump(
        state,
        "retrieve",
        "retrieved",
        {"doc_ids": [h["doc_id"] for h in top], "n": len(top)},
        started,
    )

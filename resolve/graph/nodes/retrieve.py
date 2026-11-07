import time

from resolve.config import get_settings
from resolve.graph.nodes.common import bump
from resolve.graph.state import TicketState
from resolve.retrieval.ingest import load_index
from resolve.retrieval.rerank import rerank
from resolve.retrieval.rewrite import rewrite


def retrieve_node(state: TicketState) -> TicketState:
    started = time.perf_counter()
    settings = get_settings()
    original = state.get("redacted_text") or state["raw_text"]
    rewritten = rewrite(original, settings.query_rewrite)
    index = load_index()
    hits = index.search_multi(
        rewritten.queries,
        k=settings.retrieve_k,
        mode="hybrid",
        filter_query=original,
    )
    top = rerank(original, hits, top_n=settings.rerank_top_n)
    top = [h for h in top if h.get("status") == "active"]
    state["retrieved"] = top
    state["rewrite"] = {
        "mode": rewritten.mode,
        "original": rewritten.original,
        "queries": rewritten.queries,
        "notes": rewritten.notes,
    }
    return bump(
        state,
        "retrieve",
        "retrieved",
        {
            "doc_ids": [h["doc_id"] for h in top],
            "n": len(top),
            "query_original": rewritten.original,
            "query_rewritten": rewritten.queries,
            "rewrite_mode": rewritten.mode,
            "rewrite_notes": rewritten.notes,
        },
        started,
    )

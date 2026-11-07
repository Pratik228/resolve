"""Optional cross-encoder rerank. ``RERANKER=identity`` keeps hybrid order (the CI default)."""

from __future__ import annotations

from resolve.config import get_settings

_MODELS = {"minilm": "Xenova/ms-marco-MiniLM-L-6-v2", "bge-reranker": "BAAI/bge-reranker-base"}
_LOADED: dict[str, object] = {}


def _encoder(name: str):
    if name not in _LOADED:
        from fastembed.rerank.cross_encoder import TextCrossEncoder

        _LOADED[name] = TextCrossEncoder(_MODELS[name])
    return _LOADED[name]


def rerank(query: str, hits: list[dict], top_n: int = 4, reranker: str | None = None) -> list[dict]:
    name = reranker or get_settings().reranker
    if name == "identity" or not hits:
        return [{**h, "rerank_score": None} for h in hits[:top_n]]
    scores = list(_encoder(name).rerank(query, [h["text"][:2000] for h in hits]))
    order = sorted(range(len(hits)), key=lambda i: scores[i], reverse=True)
    return [{**hits[i], "rerank_score": float(scores[i])} for i in order[:top_n]]

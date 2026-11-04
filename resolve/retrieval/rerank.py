"""Cross-encoder rerank with a lexical fallback so CI does not need GPU weights."""

from __future__ import annotations

from resolve.retrieval.hybrid import tokenize

_MODEL = None


def _lexical_score(query: str, text: str) -> float:
    q = set(tokenize(query))
    d = tokenize(text)
    if not q or not d:
        return 0.0
    overlap = sum(1 for t in d if t in q)
    return overlap / (len(q) ** 0.5)


def rerank(query: str, hits: list[dict], top_n: int = 4) -> list[dict]:
    """Cross-encoder when installed. Otherwise keep hybrid order (don't scramble with a toy score)."""
    global _MODEL
    try:
        if _MODEL is not False:
            from sentence_transformers import CrossEncoder

            if _MODEL is None:
                _MODEL = CrossEncoder("BAAI/bge-reranker-base")
            pairs = [(query, h["text"][:2000]) for h in hits]
            scores = _MODEL.predict(pairs)
            scored = sorted(zip(scores, hits, strict=False), key=lambda x: float(x[0]), reverse=True)
            out = []
            for score, hit in scored[:top_n]:
                item = dict(hit)
                item["rerank_score"] = float(score)
                out.append(item)
            return out
    except Exception:
        _MODEL = False
    return [{**h, "rerank_score": None} for h in hits[:top_n]]

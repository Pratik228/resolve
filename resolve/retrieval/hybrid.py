"""In-process hybrid search (dense + BM25 + weighted RRF). Qdrant is optional.

Dense vectors come from a pluggable embedder:
- ``hash-384``  md5 feature hashing. Deterministic, no download; the CI baseline.
- ``bge-small`` BAAI/bge-small-en-v1.5 via fastembed (ONNX on CPU, ~70 MB, no key).
"""

from __future__ import annotations

import hashlib
import math
import re
from collections import Counter, defaultdict
from dataclasses import asdict

import numpy as np

from resolve.retrieval.chunking import Chunk

DIM = 384
TOKEN_RE = re.compile(r"[A-Za-z0-9_\-]+")


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in TOKEN_RE.findall(text)]


def dense_embed(text: str) -> np.ndarray:
    """Stable hashed embedding (md5). Python's `hash()` is per-process salted and cannot snapshot."""
    vec = np.zeros(DIM, dtype=np.float32)
    for tok in tokenize(text):
        h = int(hashlib.md5(tok.encode("utf-8")).hexdigest(), 16)
        vec[h % DIM] += 1.0
    n = np.linalg.norm(vec)
    return vec / n if n else vec


def rrf(
    rank_lists: list[list[str]], k: int = 60, weights: list[float] | None = None
) -> list[tuple[str, float]]:
    """Reciprocal rank fusion. ``weights`` lets a strong sparse signal outvote a weak dense one."""
    weights = weights or [1.0] * len(rank_lists)
    scores: dict[str, float] = defaultdict(float)
    for ranks, w in zip(rank_lists, weights, strict=True):
        for rank, cid in enumerate(ranks, start=1):
            scores[cid] += w / (k + rank)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


class HashEmbedder:
    name = "hash-384"

    def embed_docs(self, texts: list[str]) -> np.ndarray:
        return np.stack([dense_embed(t) for t in texts]) if texts else np.zeros((0, DIM), np.float32)

    def embed_query(self, text: str) -> np.ndarray:
        return dense_embed(text)


class FastEmbedder:
    """bge-small-en-v1.5. Queries get bge's retrieval instruction via ``query_embed``."""

    MODELS = {"bge-small": "BAAI/bge-small-en-v1.5"}

    def __init__(self, name: str):
        from fastembed import TextEmbedding

        self.name = name
        self._model = TextEmbedding(self.MODELS[name])
        self._qcache: dict[str, np.ndarray] = {}

    def embed_docs(self, texts: list[str]) -> np.ndarray:
        vecs = np.array(list(self._model.passage_embed(texts)), dtype=np.float32)
        return vecs / np.linalg.norm(vecs, axis=1, keepdims=True)

    def embed_query(self, text: str) -> np.ndarray:
        if text not in self._qcache:
            v = np.array(next(iter(self._model.query_embed(text))), dtype=np.float32)
            self._qcache[text] = v / (np.linalg.norm(v) or 1.0)
        return self._qcache[text]


_EMBEDDERS: dict[str, object] = {}


def get_embedder(name: str):
    if name not in _EMBEDDERS:
        _EMBEDDERS[name] = HashEmbedder() if name == "hash-384" else FastEmbedder(name)
    return _EMBEDDERS[name]


def _cached_vectors(embedder, texts: list[str]) -> np.ndarray:
    """Doc vectors are cached on disk keyed by model + corpus hash so restarts don't re-embed."""
    if embedder.name == "hash-384":
        return embedder.embed_docs(texts)
    from resolve.config import get_settings

    digest = hashlib.sha256(("\x00".join(texts) + embedder.name).encode()).hexdigest()[:16]
    path = get_settings().data_dir / "index" / f"vectors-{embedder.name}-{digest}.npy"
    if path.exists():
        return np.load(path)
    vecs = embedder.embed_docs(texts)
    path.parent.mkdir(parents=True, exist_ok=True)
    np.save(path, vecs)
    return vecs


class HybridIndex:
    def __init__(self, chunks: list[Chunk], embedding_model: str | None = None, bm25_weight: float | None = None):
        from resolve.config import get_settings

        settings = get_settings()
        self.embedder = get_embedder(embedding_model or settings.embedding_model)
        self.bm25_weight = settings.hybrid_bm25_weight if bm25_weight is None else bm25_weight
        self.chunks = {c.chunk_id: c for c in chunks}
        self._docs = list(chunks)
        self._vectors = _cached_vectors(self.embedder, [c.text for c in self._docs])
        df: Counter[str] = Counter()
        self._tf: list[Counter[str]] = []
        for c in self._docs:
            tf = Counter(tokenize(c.text + " " + c.doc_id + " " + c.title))
            self._tf.append(tf)
            df.update(tf.keys())
        n = max(len(self._docs), 1)
        self._idf = {t: math.log((n + 1) / (df[t] + 0.5)) for t in df}

    def _filter(self, status: str = "active") -> list[int]:
        return [i for i, c in enumerate(self._docs) if c.status == status]

    def search(self, query: str, k: int = 20, mode: str = "hybrid", status: str = "active") -> list[dict]:
        allowed = self._filter(status)
        if not allowed:
            return []
        dense_ranks = self._dense_ranks(query, allowed)
        bm25_ranks = self._bm25_ranks(query, allowed)
        if mode == "dense":
            order = dense_ranks
        elif mode == "bm25":
            order = bm25_ranks
        else:
            # Exact tokens (NW-4031) are BM25's job; bm25_weight lets sparse outvote a weak dense model.
            fused = rrf([bm25_ranks, dense_ranks], weights=[self.bm25_weight, 1.0])
            order = [cid for cid, _ in fused]
        hits = []
        qlow = query.lower()
        for cid in order:
            chunk = self.chunks[cid]
            if chunk.doc_id == "community-tips" and "community" not in qlow:
                continue
            hits.append({**asdict(chunk), "score": 1.0})
            if len(hits) >= k:
                break
        return hits

    def _dense_ranks(self, query: str, allowed: list[int]) -> list[str]:
        q = self.embedder.embed_query(query)
        sub = self._vectors[allowed]
        if len(sub) == 0:
            return []
        sims = sub @ q
        order = np.argsort(-sims)
        return [self._docs[allowed[i]].chunk_id for i in order]

    def _bm25_ranks(self, query: str, allowed: list[int], k1: float = 1.5, b: float = 0.75) -> list[str]:
        q = tokenize(query)
        avgdl = np.mean([sum(self._tf[i].values()) or 1 for i in allowed]) if allowed else 1
        scored = []
        for i in allowed:
            tf = self._tf[i]
            dl = sum(tf.values()) or 1
            score = 0.0
            for tok in q:
                if tok not in tf:
                    continue
                idf = self._idf.get(tok, 0.0)
                f = tf[tok]
                score += idf * (f * (k1 + 1)) / (f + k1 * (1 - b + b * dl / avgdl))
            scored.append((score, self._docs[i].chunk_id))
        scored.sort(reverse=True)
        return [cid for _, cid in scored]

    def search_multi(
        self,
        queries: list[str],
        k: int = 20,
        mode: str = "hybrid",
        status: str = "active",
        filter_query: str | None = None,
    ) -> list[dict]:
        """Run each rewritten query, fuse chunk ranks with RRF, then unique-doc cut."""
        if not queries:
            return []
        rank_lists: list[list[str]] = []
        by_id: dict[str, dict] = {}
        for q in queries:
            hits = self.search(q, k=k, mode=mode, status=status)
            rank_lists.append([h["chunk_id"] for h in hits])
            for h in hits:
                by_id.setdefault(h["chunk_id"], h)
        fused = rrf(rank_lists)
        qlow = (filter_query or queries[0]).lower()
        out: list[dict] = []
        for cid, score in fused:
            chunk = by_id.get(cid) or {**asdict(self.chunks[cid]), "score": score}
            if chunk.get("doc_id") == "community-tips" and "community" not in qlow:
                continue
            item = dict(chunk)
            item["score"] = score
            out.append(item)
            if len(out) >= k:
                break
        return out

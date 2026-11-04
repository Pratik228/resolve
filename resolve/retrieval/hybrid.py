"""In-process hybrid search (dense hash + BM25 + RRF). Qdrant is optional."""

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


def rrf(rank_lists: list[list[str]], k: int = 60) -> list[tuple[str, float]]:
    scores: dict[str, float] = defaultdict(float)
    for ranks in rank_lists:
        for rank, cid in enumerate(ranks, start=1):
            scores[cid] += 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


class HybridIndex:
    def __init__(self, chunks: list[Chunk]):
        self.chunks = {c.chunk_id: c for c in chunks}
        self._docs = list(chunks)
        self._vectors = np.stack([dense_embed(c.text) for c in self._docs]) if self._docs else np.zeros((0, DIM))
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
            # Hash embeddings are coarse; duplicate BM25 ranks so exact tokens keep the lead.
            fused = rrf([bm25_ranks, bm25_ranks, dense_ranks])
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
        q = dense_embed(query)
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

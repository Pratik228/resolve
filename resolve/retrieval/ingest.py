"""Build the local hybrid index (and optionally upsert to Qdrant)."""

from __future__ import annotations

import json
from pathlib import Path

from resolve.config import get_settings
from resolve.retrieval.chunking import chunk_kb
from resolve.retrieval.hybrid import HybridIndex

_INDEX: HybridIndex | None = None


def index_path() -> Path:
    path = get_settings().data_dir / "index" / "chunks.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def ingest() -> HybridIndex:
    settings = get_settings()
    chunks = chunk_kb(settings.data_dir / "kb")
    payload = [
        {
            "chunk_id": c.chunk_id,
            "doc_id": c.doc_id,
            "title": c.title,
            "category": c.category,
            "status": c.status,
            "updated_at": c.updated_at,
            "heading": c.heading,
            "text": c.text,
            "token_estimate": c.token_estimate,
            "payload": c.payload,
        }
        for c in chunks
    ]
    index_path().write_text(json.dumps(payload, indent=2))
    if get_settings().qdrant_url and not get_settings().qdrant_url.startswith("http://localhost"):
        try:
            _upsert_qdrant(chunks)
        except Exception as exc:
            print(f"qdrant upsert skipped: {exc}")
    global _INDEX
    from resolve.retrieval.chunking import Chunk

    _INDEX = HybridIndex([Chunk(**{k: p[k] for k in Chunk.__dataclass_fields__}) for p in payload])
    print(f"ingested {len(chunks)} chunks from {len({c.doc_id for c in chunks})} docs")
    return _INDEX


def load_index() -> HybridIndex:
    global _INDEX
    if _INDEX is not None:
        return _INDEX
    path = index_path()
    if not path.exists():
        return ingest()
    from resolve.retrieval.chunking import Chunk

    payload = json.loads(path.read_text())
    _INDEX = HybridIndex([Chunk(**{k: p[k] for k in Chunk.__dataclass_fields__}) for p in payload])
    return _INDEX


def _upsert_qdrant(chunks) -> None:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, PointStruct, VectorParams

    from resolve.retrieval.hybrid import dense_embed

    settings = get_settings()
    client = QdrantClient(url=settings.qdrant_url, timeout=2)
    client.recreate_collection(
        collection_name=settings.qdrant_collection,
        vectors_config=VectorParams(size=384, distance=Distance.COSINE),
    )
    points = [
        PointStruct(
            id=i,
            vector=dense_embed(c.text).tolist(),
            payload={"chunk_id": c.chunk_id, "doc_id": c.doc_id, "status": c.status, "text": c.text},
        )
        for i, c in enumerate(chunks)
    ]
    client.upsert(collection_name=settings.qdrant_collection, points=points)


if __name__ == "__main__":
    ingest()

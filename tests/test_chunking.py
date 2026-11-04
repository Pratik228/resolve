from pathlib import Path

from resolve.config import get_settings
from resolve.retrieval.chunking import chunk_document, chunk_kb


def test_frontmatter_and_tables_kept():
    path = get_settings().data_dir / "kb" / "plans-and-pricing.md"
    chunks = chunk_document(path)
    assert chunks
    assert chunks[0].doc_id == "plans-and-pricing"
    assert chunks[0].status == "active"
    joined = "\n".join(c.text for c in chunks)
    assert "| Pro |" in joined


def test_archived_status_preserved():
    path = get_settings().data_dir / "kb" / "refund-policy-2024-archived.md"
    chunks = chunk_document(path)
    assert all(c.status == "archived" for c in chunks)


def test_kb_has_thirty_docs():
    chunks = chunk_kb(get_settings().data_dir / "kb")
    docs = {c.doc_id for c in chunks}
    assert len(docs) == 30

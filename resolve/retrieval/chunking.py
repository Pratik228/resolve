"""Markdown-aware chunking. Tables stay whole; frontmatter becomes Qdrant payload."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    title: str
    category: str
    status: str
    updated_at: str
    heading: str
    text: str
    token_estimate: int
    payload: dict = field(default_factory=dict)


FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.S)
HEADING_RE = re.compile(r"^(#{1,3}) (.+)$", re.M)


def estimate_tokens(text: str) -> int:
    return max(1, len(text.split()))


def parse_markdown(path: Path) -> tuple[dict, str]:
    raw = path.read_text()
    match = FRONTMATTER_RE.match(raw)
    if not match:
        return {}, raw
    meta = yaml.safe_load(match.group(1)) or {}
    return meta, match.group(2)


def _split_keep_tables(body: str) -> list[tuple[str, str]]:
    """Return (heading, section_text) pairs. Pipe tables are never split."""
    parts: list[tuple[str, str]] = []
    current_heading = "intro"
    buf: list[str] = []
    in_table = False
    for line in body.splitlines():
        if re.match(r"^\|", line):
            in_table = True
            buf.append(line)
            continue
        if in_table and not line.strip():
            in_table = False
            buf.append(line)
            continue
        heading = HEADING_RE.match(line)
        if heading and not in_table:
            if buf:
                parts.append((current_heading, "\n".join(buf).strip()))
            current_heading = heading.group(2).strip()
            buf = [line]
        else:
            buf.append(line)
    if buf:
        parts.append((current_heading, "\n".join(buf).strip()))
    return [(h, t) for h, t in parts if t]


def chunk_document(path: Path, target_tokens: int = 400, overlap: int = 60) -> list[Chunk]:
    meta, body = parse_markdown(path)
    doc_id = str(meta.get("doc_id") or path.stem)
    sections = _split_keep_tables(body)
    chunks: list[Chunk] = []
    idx = 0
    for heading, text in sections:
        words = text.split()
        if estimate_tokens(text) <= target_tokens or text.count("|") >= 4:
            chunks.append(_make(doc_id, meta, heading, text, idx))
            idx += 1
            continue
        start = 0
        while start < len(words):
            end = min(len(words), start + target_tokens)
            piece = " ".join(words[start:end])
            chunks.append(_make(doc_id, meta, heading, piece, idx))
            idx += 1
            if end == len(words):
                break
            start = max(end - overlap, start + 1)
    return chunks


def _make(doc_id: str, meta: dict, heading: str, text: str, idx: int) -> Chunk:
    return Chunk(
        chunk_id=f"{doc_id}::{idx}",
        doc_id=doc_id,
        title=str(meta.get("title") or doc_id),
        category=str(meta.get("category") or "unknown"),
        status=str(meta.get("status") or "active"),
        updated_at=str(meta.get("updated_at") or ""),
        heading=heading,
        text=text,
        token_estimate=estimate_tokens(text),
        payload={
            "doc_id": doc_id,
            "title": meta.get("title"),
            "category": meta.get("category"),
            "status": meta.get("status"),
            "updated_at": str(meta.get("updated_at") or ""),
            "heading": heading,
        },
    )


def chunk_kb(kb_dir: Path) -> list[Chunk]:
    chunks: list[Chunk] = []
    for path in sorted(kb_dir.rglob("*.md")):
        chunks.extend(chunk_document(path))
    return chunks

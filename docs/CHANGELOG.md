# Changelog

## 2026-11-04 — Step A foundations

`RESOLVE_LLM` defaults to `off` and the graph still does not call a model. Added a 60-case deterministic snapshot (`evals/snapshots/deterministic_v1.json`) and `tests/test_snapshot.py`; regenerate only with `make snapshot`. Results files now carry a `meta` block (git SHA, UTC time, n, LLM mode, embedding, reranker, backend, package versions) via `evals/meta.py`. `make report` rewrites the README results section from `evals/results/*.json`. README stack line is the custom 11-node runner; LangGraph / Qdrant / Redis / Langfuse / DeepEval / cross-encoder are not claimed for the default path.

Hashed dense vectors now use md5 instead of builtin `hash()`, which is salted per process and cannot freeze a snapshot. Policy engine unchanged.

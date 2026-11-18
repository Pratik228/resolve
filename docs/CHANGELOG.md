# Changelog

## 2026-11-09: Hardening, Claude layer, reliability evals, redesign

- Fixed: SLA credits scoped to the requested month; every eval threshold now asserted in CI; public `auto_approve` removed and CORS tightened; "sue" matched inside "issue"; chargebacks escalate; draft retries no longer echo rejected amounts into replies; idempotency is per customer + item, not per ticket (453 duplicate refunds found in dev); one golden label corrected (claim vs ledger).
- Added: Claude triage + drafting (`RESOLVE_LLM=off|replay|live`, structured outputs, spend cap) with recorded outputs that are not blind; pass^k reliability on ledger end-state (108 variants); bge-small hybrid retrieval chosen on a dev split; load test (7.3 → ~97 tickets/s); Break the refund red-team API; demo reset; production compose behind a Cloudflare Tunnel.
- Web: redesigned as security-printed cheques (explainer, console, trace, approvals, evals, red-team).

## 2026-11-06 — Query rewrite (optional)

Added `QUERY_REWRITE=off|rules|llm` before retrieval. `rules` expands `NW-****` codes and abbreviations, strips greetings/signatures, splits multi-question tickets, and fuses sub-queries with RRF. `llm` is wired but skipped while `RESOLVE_LLM=off` (redacted text only, max 3 JSON queries). Original + rewritten queries are logged on the retrieve audit event. Ablation now reports hybrid with and without rewrite (Recall@4, MRR, p50/p95). Default stays `off` unless the measured decision says rules wins; the deterministic snapshot is not regenerated.

## 2026-11-04 — Step A foundations

`RESOLVE_LLM` defaults to `off` and the graph still does not call a model. Added a 60-case deterministic snapshot (`evals/snapshots/deterministic_v1.json`) and `tests/test_snapshot.py`; regenerate only with `make snapshot`. Results files now carry a `meta` block (git SHA, UTC time, n, LLM mode, embedding, reranker, backend, package versions) via `evals/meta.py`. `make report` rewrites the README results section from `evals/results/*.json`. README stack line is the custom 11-node runner; LangGraph / Qdrant / Redis / Langfuse / DeepEval / cross-encoder are not claimed for the default path.

Hashed dense vectors now use md5 instead of builtin `hash()`, which is salted per process and cannot freeze a snapshot. Policy engine unchanged.

# Design decisions

Resolve is built as a **production-shaped** support engine, not a chatbot demo.

## What owns what

| Concern | Owner |
|---|---|
| Wording, classification, tool plan, citations | LLM nodes (or deterministic stand-ins when no API key) |
| Refund / SLA credit amounts and eligibility | `resolve/policy/engine.py` |
| Writes | `finalize` + unique `idempotency_key` |
| Anything ≥ $100 or Enterprise | Human interrupt |
| “Did we get worse?” | `evals/` + GitHub Action |

Line for interviews: **LLMs decide what to say; code decides what’s allowed.**

## Why an explicit graph instead of a free-form ReAct loop

ReAct lets the model call `refund()` when a ticket yells loudly enough. An 11-node graph with a step cap of 12 makes every failure path terminate at a human. Retrieval and account tools fan out, then join at `policy_gate`, so the model never sees raw PII and never does arithmetic on money.

The runtime used in the CLI and API is `resolve/graph/runner.py`. `resolve/graph/build.py` compiles the same nodes with LangGraph when that extra is installed. That split exists because LangGraph’s interrupt/checkpointer APIs move; the policy and eval contracts should not.

## Retrieval

Error codes like `NW-4031` are exact tokens. Dense hash/embeddings miss them; BM25 catches them; RRF fuses ranks without score calibration. Archived docs are payload-filtered (`status=active`) so the 2024 30-day refund policy cannot sneak into a live answer.

Ablation lives in `evals/ablation.py`. The README table is whatever that script last wrote — never hand-waved.

## What we would do next

- Swap hashed embeddings for `fastembed` / a hosted embedding API and re-run ablation.
- Postgres checkpointer for paused approvals across process restarts (SQLite is the local stand-in).
- DeepEval judge model on a different tier than the drafter.
- v2: BYO GitHub repo scorecard (`docs/SPEC.md`).

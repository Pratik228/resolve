# Resolve — Build Spec

**Name:** Resolve, an eval-gated agentic Tier-2 support engine.

**One-liner:** An agentic support resolver that answers Tier-2 tickets from a company KB and live account data, executes refunds and credits only through a deterministic policy engine with human approval, and blocks every deploy that regresses on a 60-case golden + adversarial eval suite.

**Company:** Northwind Cloud (fictional B2B SaaS). Plans: Starter $29 / Pro $49 / Enterprise $299 monthly. Error codes `NW-4031`–`NW-4040`.

## Differentiators

1. Deterministic policy engine — LLM drafts words; Python decides money.
2. Human-in-the-loop approval over $100 or Enterprise (`interrupt` / runner pause).
3. Eval-gated CI on every PR touching `resolve/**`, `data/kb/**`, `evals/**`.
4. Retrieval ablation table (dense / BM25 / hybrid / hybrid+rerank).
5. Adversarial suite: injection, PII probes, archived-policy bait, fake CEO promises.
6. Production signals: audit log, idempotent writes, step cap 12, optional Langfuse.

## Graph

`redact → injection_scan → classify` then escalate if legal/deletion/contract, else `plan → retrieve ∥ tools → policy_gate → draft → validate` (retry draft twice) → `approval` if needed → `finalize` / `escalate`.

## Data

30 KB docs in `data/kb/` with YAML frontmatter. Archived refund policy. Planted injection in `community-tips.md`. Seed: 40 customers, ~150 invoices, 3 deliberate duplicates (`cus_014` $49, `cus_022` $29, `cus_008` $900), 5 incidents, 400 usage rows. Golden set: `evals/golden.jsonl` (60).

## Policy rules (must match tests)

- Duplicate charges always refundable, including Enterprise annual.
- Full refund day 0–14 inclusive; prorate day 15+.
- Enterprise annual otherwise $0.
- Auto-approve ≤ $100 and plan ∈ {Starter, Pro}; else human.
- SLA: Starter 99.5% / 5% per 0.1% / cap 20%; Pro 99.9% / 10% / 30%; Enterprise 99.95% / 15% / 50%.
- Duplicate refund and SLA credit do not stack on one ticket.

## v2 (not in v1 runtime)

Bring-your-own public GitHub repo: ingest docs + closed issues, hold out 50, scorecard + missing-docs clusters. No write actions.

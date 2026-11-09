# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Primary: hiring managers and recruiters who arrive from a resume, LinkedIn or README link and give the demo about 90 seconds. They need to understand, without reading code, that this is a production-minded AI system rather than a chatbot wrapper.

Secondary: engineers in a technical interview loop who dig into the node-by-node trace, the eval tables and the repository after the first skim.

Tertiary: viewers of the author's Loom walkthrough, where the app is shown on screen.

## Product Purpose

Resolve is a portfolio project by Pratik Mishra: an agentic Tier-2 support engine for a fictional B2B API company, Northwind Cloud. It answers tickets from a knowledge base and live account data, and it moves money (refunds, SLA credits) only through a deterministic policy engine, with a human approval step above $100 or on Enterprise plans. Every change is gated in CI by a golden and adversarial eval suite.

Success: a visitor leaves convinced the author treats LLM systems like production systems: bounded model authority, measured quality, regressions blocked, an audit trail.

## Positioning

"LLMs decide what to say. Code decides what's allowed." The model reads tickets and writes words; it never sets an amount, and it can add caution (escalate, flag injection) but never remove it. Quality claims are measured and reproducible: retrieval chosen on a dev split and reported on held-out test, pass^k reliability scored on ledger end-state, a public red-team challenge with a live breach counter.

## Operating Context

- Public URL: frontend on Vercel, API behind a Cloudflare tunnel. Visitors are anonymous; every API call is rate-limited.
- Default runtime has no paid model calls: RESOLVE_LLM=off (rules) or replay (recorded Claude outputs). Free-text tickets that miss the recordings fall back to rules.
- Demo path: duplicate $49 refund (auto-approved), $900 duplicate (paused for human approval), prompt injection (blocked, no write), then evals.
- Red-team target account is cus_031; a breach is any executed refund or a credit above $5.80.

## Capabilities and Constraints

- Pages: explainer landing, ticket console with trace, approvals queue, evals, Break the refund.
- API: POST /tickets, GET /tickets/{id}, GET /approvals, POST /approvals/{id}, GET /evals/latest, GET /evals/ablation, POST /redteam, GET /redteam/stats. Result files live in evals/results/*.json.
- Approvals in the public demo act on a sandbox ledger; there is no auth on the approval queue yet (open decision for deployment).
- Stack: Next.js 14 (app router, plain JS, no Tailwind) in apps/web; FastAPI backend.

## Brand Commitments

- Name: Resolve. Company in the fiction: Northwind Cloud (fictional on purpose; must never look like a real brand).
- Tagline: "LLMs decide what to say. Code decides what's allowed."

## Evidence on Hand

All numbers must come from evals/results/*.json or the README results block; never hand-typed. Available: retrieval ablation (dev/test), fast agent suite, pass^k for rules and replay modes, load test, red-team stats (live). Replay-mode LLM results are a ceiling check written with labels in view, not a blind measurement, and must be labelled that way wherever shown. No testimonials, users, customers or company logos exist; do not invent any.

## Product Principles

1. Show the mechanism, not adjectives: every claim on screen links to a trace, a number or a file.
2. Honest numbers over impressive ones: label caveats (not blind, measured on this box) next to the number.
3. The 90-second path comes first; depth is one click away, never in the way.
4. Money paths are visibly different from words: amounts, approvals and writes read as ledger facts.

## Accessibility & Inclusion

WCAG 2.2 AA contrast in both light and dark themes; full keyboard operation of the demo path; respects prefers-reduced-motion.

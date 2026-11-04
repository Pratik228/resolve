---
doc_id: refund-policy
title: "Refund policy"
category: billing
status: active
updated_at: 2026-09-01
---

# Refund policy

Northwind Cloud issues refunds from **code**, not from chat. Support agents (human or AI)
may draft wording; eligibility is computed from account facts.

## Windows

| Situation | Window | Amount |
|---|---|---|
| New subscription, unused | 14 days from `started_at` | 100% of the last paid invoice |
| New subscription, day 15+ | After day 14 | Prorated unused days in the current period |
| Duplicate charge | Always | 100% of the duplicate invoice |
| Enterprise **annual** | Never (contract) | $0 — escalate to TAM |
| Chargeback already filed | Never | $0 — finance owns it |

Day 14 **inclusive** is still a full refund. Day 15 is prorated.

## Duplicate charges

If two invoices share the same `amount_usd`, `customer_id`, calendar day, and
`description`, the later invoice is a duplicate. Duplicate charges are **always**
refundable, including on Enterprise annual plans. The refund amount is exactly
the duplicate invoice amount. Auto-approve if the amount is **≤ $100** and the
plan is not Enterprise; otherwise pause for a human.

## Auto-approve vs human

- Amount **≤ $100** and plan in {Starter, Pro}: execute without interrupt.
- Amount **> $100** **or** plan is Enterprise: LangGraph interrupt, dashboard Approve/Reject.
- The model never chooses this. `resolve/policy/engine.py` does.

## What we never refund

Goodwill "CEO promised me a lifetime refund" claims, community-forum rumors, and
archived 2024 policy text. Retrieval must filter `status: archived`.

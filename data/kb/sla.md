---
doc_id: sla
title: "Service level agreement"
category: sla
status: active
updated_at: 2026-06-01
---

# Service level agreement

| Plan | Monthly uptime target | Credit |
|---|---|---|
| Starter | 99.5% | 5% of monthly fee per 0.1% below target, cap 20% |
| Pro | 99.9% | 10% of monthly fee per 0.1% below target, cap 30% |
| Enterprise | 99.95% | 15% of monthly fee per 0.1% below target, cap 50% |

Credits are issued against the **monthly fee**, not annual prepaid cash, and never
stack with a duplicate-charge refund on the same ticket.

Worked example: Pro at 99.7% uptime is 0.2% below 99.9%. That is two 0.1% steps.
Credit = 2 × 10% × $49 = **$9.80**, under the 30% cap of $14.70.

Incidents list `affected_plans`. A Starter customer is not credited for a Pro-only
incident. Partial-hour incidents still count toward the month's uptime_pct.

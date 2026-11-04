---
doc_id: billing-cycles
title: "Billing cycles"
category: billing
status: active
updated_at: 2026-07-01
---

# Billing cycles

Invoices issue on the `renews_at` day in the customer's region timezone, converted
to UTC in the ledger. Monthly plans invoice the plan fee plus usage from the prior
period. Failed payments retry on day 3 and day 7, then the subscription `past_due`.

A customer who sees two invoices on the **same UTC day** with the same amount
should open a billing ticket; that is the duplicate-charge path, not a cycle bug.

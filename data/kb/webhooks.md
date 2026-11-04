---
doc_id: webhooks
title: "Webhooks"
category: technical
status: active
updated_at: 2026-07-20
---

# Webhooks

Events: `invoice.paid`, `invoice.failed`, `incident.opened`. Retry 8 times with exponential backoff. Signature header `X-Northwind-Signature`.

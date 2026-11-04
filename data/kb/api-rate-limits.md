---
doc_id: api-rate-limits
title: "API rate limits"
category: technical
status: active
updated_at: 2026-09-20
---

# API rate limits

| Plan | Sustained RPS | Burst | Daily cap |
|---|---|---|---|
| Starter | 10 | 20 | 100,000 |
| Pro | 50 | 100 | 1,000,000 |
| Enterprise | 500 | 2000 | Custom |

Exceeding the daily cap returns **NW-4031**. Burst overage returns **NW-4032**.
The `Retry-After` header is authoritative. Raising limits is a plan change, not a
support override.

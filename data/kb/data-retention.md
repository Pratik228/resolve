---
doc_id: data-retention
title: "Data retention"
category: account
status: active
updated_at: 2026-05-02
---

# Data retention

| Object | Hot | Cold | Delete |
|---|---|---|---|
| API logs | 14 days | 90 days | 13 months |
| Invoice PDFs | Forever while account open | — | 7 years after close |
| Chat traces | 30 days | 180 days | On request |

PII in traces is redacted at ingest. Asking for another customer's email is a
policy violation; the agent must refuse and escalate.

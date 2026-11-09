# Build log: phases and what's pending

This file lists what was built, phase by phase, and what is still open. Commit hashes are on `feat/query-rewrite`. For the short version, see [CHANGELOG.md](CHANGELOG.md).

## Phase 0. Foundations (4–7 Nov, Pratik)

| Commit | What |
|---|---|
| v0 … `3c18693` | 11-node graph runner, deterministic policy engine (refunds, SLA credits), PII redaction, validator grounding, 60-case golden + adversarial suite, deterministic snapshot, results `meta` block, generated README scores |
| `aa572eb` | GitHub Actions workflow that runs the evals on every PR |
| `bf0e164` | Stopped publishing the local DB password; compose ports bound to 127.0.0.1 |
| `0f7c0e3` | Optional query rewrite (`QUERY_REWRITE=off\|rules\|llm`) before hybrid retrieval |

## Phase 1. Get it running (9 Nov, with Claude Code)

There is no commit for this phase; it was environment setup only.

- Installed: uv with Python 3.11 (`.venv`), Node 22 under `/root/.local`, `make` and `gh` from apt, and Playwright Chromium for screenshots.
- Ran `make seed && make ingest`, then the tests and evals.
- Started the API on `127.0.0.1:8000` and the web app on `127.0.0.1:3000`. Nothing is exposed publicly, and `/opt/ai-receptionist` was not touched.

## Phase 2. Correctness and safety fixes (`4d651ef`)

- **CI gate:** CI only asserted 0.60 while the README claimed 0.90. Every threshold in `evals/thresholds.yaml` is now enforced. Action correctness was really 0.88; after the fixes it is 0.96.
- **SLA credit:** the credit used the worst incident on record. It is now scoped to the month asked about, so $14.70 became the correct $9.80.
- **Public API:** callers could pass `auto_approve` and skip human approval. That flag is removed. CORS is tightened.
- **Legal keyword:** "sue" matched inside "issue". Matching is now anchored to word starts.
- **Chargebacks** now escalate.

## Phase 3. Retrieval (`870f1b0`)

- Replaced hashed vectors with real embeddings: `BAAI/bge-small-en-v1.5` via fastembed, CPU-only.
- BM25 and dense results are combined with weighted RRF. The weights were chosen on a dev split and are reported on a held-out test split.
- Held-out Recall@4 went from 0.75 to 0.80.
- The `ms-marco-MiniLM-L-6` cross-encoder was tested and rejected: Recall@4 fell from 0.81 to 0.77, at about 1 s per query.

## Phase 4. Reliability: pass^k (`474b2d9`)

- τ-bench-style pass^k: 27 money cases, each phrased 5 ways (108 variants), scored on the final ledger state rather than the reply text.
- Unsafe writes are gated at 0.
- Result with rules only: pass^5 = 0.56, with 0 unsafe writes in 135 trials.

## Phase 5. Claude layer (`b6c2db5`)

- `RESOLVE_LLM=off|replay|live`, using the Anthropic SDK `messages.parse` with Pydantic schemas (`Triage`, `DraftOut`) and a spend cap.
- Merge rule: the model can add caution (escalate, flag injection) but can never remove it or set an amount.
- Replay recordings are keyed by a hash of the prompt version and the input. They were written in-session with the labels in view, so they are **not blind**.
- This work exposed and fixed three bugs: `out_of_scope` was missing from the schema, a gold label was wrong (`multi-auth-brownout`), and draft retries echoed the rejected amount into the reply.

## Phase 6. Money safety, speed, red team (`a170ea9`)

- **Double payout:** one $49 duplicate had been refunded 453 times, because the idempotency key was per ticket.
  - The key is now customer + type + item (an invoice ID or `sla:plan:YYYY-MM`).
  - A read-only `get_payouts` tool tells the engine what has already been paid, and the DB unique constraint catches races.
  - `tests/test_no_double_payout.py` covers it, including 6 concurrent tickets.
- **Throughput:** 7.3 → 56 tickets/s on 1 worker and about 97/s on 4. 85% of each ticket's time was DB overhead; the fixes were schema init once, batched audit writes, and SQLite WAL. Postgres cuts p99 by 3.4× at 16 concurrent requests.
- **Break the refund** red-team API: per-IP rate limits (aware of `CF-Connecting-IP`) and a public tally. So far there are 0 breaches in 14 attempts.
- **Startup seeding race** across workers fixed with a file lock.

## Phase 7. Web redesign (`052eee2`)

- Next.js app redesigned as security-printed cheques, in light ("paper") and dark ("carbon copy") themes.
- Pages: explainer landing, console, trace, approvals (grouped), evals, red team.
- The landing page runs the 90-second demo: three real tickets, a $900 approval, and a re-sent duplicate that is refused.

## Phase 8. README and docs (`dd50efe`)

- README rewritten: demo path, architecture coloured by owner (code, model, person), and generated pass^k and load-test tables.
- The "What the evals caught" and "Honest limits" sections were added.

## Phase 9. Deploy prep (`a542382`)

- Production `Dockerfile` and `deploy/docker-compose.prod.yml`:
  - read-only filesystem
  - capped at 1.5 CPU and 1.2 GB
  - no published ports except 127.0.0.1:8100
  - its own `cloudflared`
- Smoke-tested in replay mode, at about 730 MB RAM, then stopped.
- Steps are in [deploy/DEPLOY.md](../deploy/DEPLOY.md). The planned cost is $0 extra: this box + Cloudflare Tunnel + Vercel Hobby.

## Phase 10. Publish (this commit)

- Branch `feat/query-rewrite` pushed to GitHub. It is not merged into `main`.

---

## Pending

### Needs Pratik (accounts, keys, decisions)

1. **Deploy.** This needs:
   - a Cloudflare tunnel token and an `api.<domain>` hostname
   - a Vercel project with root `apps/web` and `NEXT_PUBLIC_API_URL` set
   - `WEB_ORIGIN` set to the Vercel URL

   Then smoke-test the 90-second path and add the live link to the README.
2. **Open a PR and merge to `main`** once CI passes on GitHub.
3. **Record the Loom.** The script is `LOOM_SCRIPT.md`, which is local only and not in git. Check its authorship section first.
4. **Blind live Claude eval.** This needs an `ANTHROPIC_API_KEY` and costs money (small, under the spend cap). It would replace the not-blind 1.00 with a real number.
5. **Decide on the history in `a170ea9`.** That commit accidentally included two SQLite helper files (`resolve.db-wal`, `resolve.db-shm`) with synthetic data only. They are untracked from the next commit, but they are still in the history.

### Not verified yet

- **GitHub CI:** the first run on GitHub has not been checked.
- **Design review:** no independent reviewer agent was available, so there was no outside design review. Two rounds of screenshot review were done in-session.

### Before anything real (beyond a portfolio demo)

- **Auth on approvals:** the approvals queue is public by design. Put it behind auth; Cloudflare Access on `/approvals*` is quickest.
- **Postgres in production** instead of SQLite. The load test already supports this.
- **Redis-backed rate limits**, so limits hold across replicas.
- **A queue for live LLM calls**, so model latency does not hold request threads.

### Housekeeping

- The dev servers (API :8000, web :3000) are still running in the background; stop them when you're done.
- Optional: rename the server hostname (`hostnamectl set-hostname …`).

# Deploying the public demo

Recommended: **API on the existing Hetzner box behind a Cloudflare Tunnel, web on Vercel.** Incremental cost: **$0/month**.

| Piece | Where | Cost | Why |
|---|---|---|---|
| Web (Next.js) | Vercel Hobby | $0 | Static-first pages, global CDN, preview deploys per PR. Hobby is for non-commercial use, which a portfolio is. |
| API (FastAPI) | Hetzner CX33 you already pay for, Docker | $0 extra | ~730 MB RAM and ≤1.5 vCPU, capped in compose so the business app keeps its headroom. |
| Ingress | Cloudflare Tunnel on your domain | $0 | No open ports: cloudflared dials out; TLS, DDoS protection and the real client IP (`CF-Connecting-IP`) come for free. |
| LLM | none by default (`RESOLVE_LLM=replay`) | $0 | Live Claude is opt-in, behind `DEMO_SPEND_CAP_USD`. |

Considered and not chosen: Fly.io, Render or Railway at roughly $5–7/month. They fully isolate the demo from the business app, but they add an account and a bill and give nothing the capped container does not. Move there if the demo ever gets real traffic.

## Steps

1. **Cloudflare** (dashboard, Zero Trust → Networks → Tunnels): create a tunnel named `resolve`, choose Docker, and copy the token. Add the public hostname `api.<your-domain>`, service `http://api:8000`. This tunnel is separate from the ai-receptionist tunnel.
2. **Server**:
   ```bash
   cp deploy/.env.prod.example deploy/.env.prod   # fill WEB_ORIGIN, IP_HASH_SALT, CLOUDFLARE_TUNNEL_TOKEN
   docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env.prod up -d --build
   curl -s 127.0.0.1:8100/health
   ```
3. **Vercel**: import the GitHub repo, set the root directory to `apps/web`, and add `NEXT_PUBLIC_API_URL=https://api.<your-domain>`. Then put the Vercel URL into `WEB_ORIGIN` and restart the API.
4. Smoke-test the 90-second path on the public URL, then add it to the README (`<!-- LIVE-DEMO -->`).

## Operating notes

- Production data lives in the `resolve_prod_var` volume. Evals never run against it; they use the dev `resolve.db`.
- Abuse: per-IP limits (tickets 20/min, red-team 10/min, demo reset 6/min), 4,000-character input cap, read-only container filesystem, no new privileges.
- The approval queue is public by design for the demo. Before anything real, put approvals behind auth (Cloudflare Access on `/approvals*` is the quickest).
- Scaling past one box: Postgres (`DATABASE_URL`, measured in the README load test), Redis-backed rate limits, more API replicas behind the same tunnel, and a queue for live LLM calls so model latency does not hold request threads.

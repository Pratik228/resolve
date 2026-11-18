"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import Cheque from "../../../components/Cheque";
import { api } from "../../../lib/api";
import { chequeFromTicket } from "../../../lib/format";

const OWNER = {
  redact: "code",
  injection_scan: "code",
  classify: "model",
  plan: "model",
  retrieve: "code",
  tools: "code",
  policy_gate: "code",
  draft: "model",
  validate: "code",
  approval: "human",
  finalize: "code",
  escalate: "code",
};

function summarize(e) {
  const p = e.payload || {};
  switch (e.node) {
    case "redact":
      return p.tokens?.length ? `masked ${p.tokens.join(", ")}` : "nothing to mask";
    case "injection_scan":
      return p.flags?.length ? `flags: ${p.flags.join(", ")}` : "no injection patterns";
    case "classify": {
      const src = p.llm && typeof p.llm === "object" ? `model (${p.llm.source})` : "rules";
      return `${p.category} · by ${src}${p.llm?.intents?.length ? ` · intents ${p.llm.intents.join(", ")}` : ""}`;
    }
    case "plan":
      return (p.tools || []).join(", ");
    case "retrieve":
      return (p.doc_ids || []).join(", ");
    case "tools":
      return Object.entries(p)
        .map(([k, v]) => `${k}${typeof v === "number" ? `×${v}` : ""}`)
        .join(", ");
    case "policy_gate":
      if (e.event === "blocked_injection") return `blocked: ${(p.flags || []).join(", ")}`;
      return p.type ? `${p.type} $${Number(p.amount_usd).toFixed(2)} · ${p.reason}` : p.reason || "no action";
    case "draft":
      return `${p.source ? `model draft (${p.source})` : "template draft"} · cites ${(p.citations || []).join(", ") || "none"}`;
    case "validate":
      return p.reasons?.length ? `rejected: ${p.reasons.join("; ")}` : "grounded · policy ok · no PII";
    case "approval":
      return e.event;
    case "finalize":
      return p.action ? `${p.action.deduped ? "deduped, not paid" : "wrote"} ${p.action.type} $${Number(p.action.amount_usd).toFixed(2)}` : "no write";
    case "escalate":
      return `to the ${p.category || "human"} queue`;
    default:
      return e.event;
  }
}

export default function TicketPage({ params }) {
  const { id } = params;
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function load() {
    try {
      setData(await api(`/tickets/${id}`));
    } catch (e) {
      setError(e.message);
    }
  }

  useEffect(() => {
    load();
  }, [id]);

  async function decide(decision) {
    setBusy(true);
    try {
      await api(`/approvals/${id}`, { method: "POST", body: JSON.stringify({ decision, approver: "you, on the demo" }) });
      await load();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  if (error && !data)
    return (
      <div className="page">
        <div className="wrap">
          <p className="error">{error}</p>
        </div>
      </div>
    );
  if (!data)
    return (
      <div className="page">
        <div className="wrap">
          <p className="empty">Loading the trace…</p>
        </div>
      </div>
    );

  const state = data.state || {};
  const events = state.events || [];
  const c = chequeFromTicket(data);
  const action = c.action;
  const total = events.reduce((s, e) => s + (e.duration_ms || 0), 0);

  return (
    <div className="page">
      <div className="wrap">
        <div className="page__head">
          <p className="num small muted">
            {data.id} · {data.customer_id} · {data.status.replace("_", " ")}
          </p>
          <h1>The trace</h1>
          <p className="reply" style={{ fontFamily: "var(--f-mono)", fontSize: "0.95rem" }}>
            &ldquo;{data.raw_text}&rdquo;
          </p>
        </div>

        <div className="split">
          <div className="stackv">
            <Cheque
              kind={c.kind}
              serial={data.id}
              payee={`Customer ${data.customer_id}`}
              amount={action?.amount_usd}
              memo={action ? action.reason : (state.policy_note && state.policy_note.reason) || "No payout on this ticket"}
              signer={state.approver && state.approver !== "auto" ? state.approver : "Policy engine"}
              flags={c.flags}
              micr={{ ticket: data.id.replace("tkt_", ""), account: data.customer_id, ref: action?.target_ref }}
              onSign={c.kind === "pending" ? () => decide("approve") : undefined}
              onVoid={c.kind === "pending" ? () => decide("reject") : undefined}
              busy={busy}
            />
            <section className="panel stackv" aria-labelledby="reply-title">
              <h2 id="reply-title" style={{ fontSize: "1.4rem" }}>
                Reply sent to the customer
              </h2>
              <p className="reply">{data.reply || "No reply yet: the ticket is waiting for a human."}</p>
              {state.draft?.cited_doc_ids?.length ? (
                <div className="chips" aria-label="Cited knowledge-base documents">
                  {state.draft.cited_doc_ids.map((d) => (
                    <span key={d} className="chip">
                      {d}
                    </span>
                  ))}
                </div>
              ) : null}
              <p className="note">
                {state.draft?.source === "replay"
                  ? "Drafted by Claude (recorded output), then checked by the validator."
                  : "Drafted by the deterministic template, then checked by the validator."}
              </p>
            </section>
          </div>

          <section aria-labelledby="trace-title" className="stackv">
            <h2 id="trace-title" style={{ fontSize: "1.6rem" }}>
              Every step, as it ran
            </h2>
            <p className="muted small">
              {events.length} steps · {total.toFixed(1)} ms in the graph. Blue steps are code, black are the model, amber
              is a person.
            </p>
            <ol className="trace">
              {events.map((e, i) => {
                const owner = OWNER[e.node] || "code";
                return (
                  <li key={i}>
                    <span className="step">{String(e.step || i + 1).padStart(2, "0")}</span>
                    <span className={`node node--${owner}`}>{e.node === "classify" ? "triage" : e.node}</span>
                    <span className="what">{summarize(e)}</span>
                    <span className="ms">{Number(e.duration_ms || 0).toFixed(1)} ms</span>
                  </li>
                );
              })}
            </ol>
            <dl className="kv">
              <dt>Category</dt>
              <dd>{state.classification?.category || "—"}</dd>
              <dt>Triage source</dt>
              <dd>{state.triage ? `${state.triage.model} (${state.triage.source})` : "rules"}</dd>
              <dt>Injection flags</dt>
              <dd>{(state.injection_flags || []).join(", ") || "none"}</dd>
              <dt>Idempotency target</dt>
              <dd>{action?.target_ref || "—"}</dd>
            </dl>
            <p>
              <Link className="textlink" href="/console">
                Send another ticket
              </Link>
            </p>
          </section>
        </div>
      </div>
    </div>
  );
}

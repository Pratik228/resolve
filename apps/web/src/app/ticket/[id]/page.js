"use client";

import { useEffect, useState } from "react";
import { api } from "../../../lib/api";

export default function TicketPage({ params }) {
  const { id } = params;
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api(`/tickets/${id}`)
      .then(setData)
      .catch((e) => setError(String(e.message || e)));
  }, [id]);

  if (error) return <p className="muted">{error}</p>;
  if (!data) return <p className="muted">Loading…</p>;

  const state = data.state || {};
  const events = state.events || [];
  const action = state.proposed_action;

  return (
    <>
      <p className="kicker">{data.id}</p>
      <div className="row" style={{ justifyContent: "space-between" }}>
        <h1>Ticket</h1>
        <span className={`status ${data.status}`}>{data.status}</span>
      </div>
      <p className="lede">{data.raw_text}</p>

      <div className="grid" style={{ gridTemplateColumns: "1.2fr 0.8fr", gap: 16 }}>
        <section className="card">
          <p className="kicker">Reply</p>
          <p style={{ marginTop: 12, lineHeight: 1.6 }}>{data.reply || "—"}</p>
          {(state.retrieved || []).map((c) => (
            <span className="chip" key={c.chunk_id || c.doc_id}>
              {c.doc_id}
            </span>
          ))}
        </section>
        <section className="card">
          <p className="kicker">Policy engine</p>
          {action ? (
            <>
              <p className="metric" style={{ marginTop: 10 }}>
                <span className="n">
                  ${Number(action.amount_usd).toFixed(2)}
                </span>
              </p>
              <p>
                {action.type} · {action.needs_approval ? "needs human" : "auto-approve"}
              </p>
              <p className="muted" style={{ marginTop: 8 }}>
                {action.reason}
              </p>
            </>
          ) : (
            <p style={{ marginTop: 10 }}>No write. The model did not get a refund tool.</p>
          )}
          {state.injection_flags?.length ? (
            <p className="muted" style={{ marginTop: 12 }}>
              Flags: {state.injection_flags.join(", ")}
            </p>
          ) : null}
        </section>
      </div>

      <h2 style={{ fontFamily: "var(--legal)", fontWeight: 500, margin: "28px 0 14px" }}>
        Trace
      </h2>
      <div className="timeline">
        {events.map((ev) => (
          <div className="t-item" key={`${ev.step}-${ev.node}`}>
            <div className="row" style={{ justifyContent: "space-between" }}>
              <strong>
                {ev.node}
                <span className="muted"> · {ev.event}</span>
              </strong>
              <span className="mono muted">{ev.duration_ms} ms</span>
            </div>
            <pre className="mono muted" style={{ whiteSpace: "pre-wrap", marginTop: 6 }}>
              {JSON.stringify(ev.payload, null, 2)}
            </pre>
          </div>
        ))}
      </div>
    </>
  );
}

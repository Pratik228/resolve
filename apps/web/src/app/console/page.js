"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "../../lib/api";
import { DEMO } from "../../lib/format";
import { Arrow } from "../../components/Icon";

const PRESETS = [
  ...DEMO.map((d) => ({ label: d.expect, customer_id: d.customer_id, text: d.text })),
  { label: "SLA credit for one month (Pro, 99.7%)", customer_id: "cus_003", text: "Pro uptime was 99.7% in September. Do I get an SLA credit?" },
  { label: "Legal threat: escalates, no write", customer_id: "cus_010", text: "We will sue you unless you refund the annual contract." },
  { label: "Exact error code retrieval", customer_id: "cus_005", text: "What does error NW-4031 mean and how do I fix it?" },
];

const CUSTOMERS = [
  ["cus_014", "Pro, has a $49 duplicate"],
  ["cus_008", "Pro, has a $900 services duplicate"],
  ["cus_003", "Pro, September incident"],
  ["cus_010", "Enterprise annual"],
  ["cus_001", "Starter, nothing refundable"],
  ["cus_005", "Starter"],
  ["cus_031", "Starter, the red-team target"],
];

export default function Console() {
  const router = useRouter();
  const [text, setText] = useState(PRESETS[0].text);
  const [customer, setCustomer] = useState(PRESETS[0].customer_id);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [tickets, setTickets] = useState(null);

  useEffect(() => {
    api("/tickets")
      .then(setTickets)
      .catch((e) => {
        setTickets([]);
        setError(e.message);
      });
  }, []);

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const t = await api("/tickets", { method: "POST", body: JSON.stringify({ text, customer_id: customer }) });
      router.push(`/ticket/${t.id}`);
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  }

  return (
    <div className="page">
      <div className="wrap">
        <div className="page__head">
          <h1>Console</h1>
          <p>
            Send any ticket as any demo customer. It runs the full graph and opens the trace. Free text that was never
            recorded uses the rules path; nothing here calls a paid model.
          </p>
        </div>
        <div className="split">
          <form className="panel stackv" onSubmit={submit} aria-label="New ticket">
            <div className="field">
              <label htmlFor="customer">Customer</label>
              <select id="customer" className="select" value={customer} onChange={(e) => setCustomer(e.target.value)}>
                {CUSTOMERS.map(([id, desc]) => (
                  <option key={id} value={id}>
                    {id} · {desc}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label htmlFor="ticket">Ticket</label>
              <textarea
                id="ticket"
                className="textarea"
                value={text}
                maxLength={4000}
                onChange={(e) => setText(e.target.value)}
              />
            </div>
            <div className="hero__actions">
              <button className="btn" disabled={busy || text.trim().length < 3}>
                {busy ? "Running the graph…" : "Send ticket"} <Arrow />
              </button>
              {error ? (
                <span className="error" role="alert">
                  {error}
                </span>
              ) : null}
            </div>
            <div className="field">
              <span className="cap">Presets</span>
              <div className="presets">
                {PRESETS.map((p) => (
                  <button
                    type="button"
                    key={p.text}
                    className="preset"
                    aria-pressed={text === p.text && customer === p.customer_id}
                    onClick={() => {
                      setText(p.text);
                      setCustomer(p.customer_id);
                    }}
                  >
                    <strong>{p.label}</strong>
                    <span className="num">
                      {p.customer_id} · {p.text}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          </form>

          <section aria-labelledby="register-title" className="stackv">
            <h2 id="register-title" style={{ fontSize: "1.6rem" }}>
              Register
            </h2>
            <p className="muted small">The last 50 tickets anyone sent on this sandbox.</p>
            {tickets === null ? (
              <p className="empty">Loading the register…</p>
            ) : tickets.length === 0 ? (
              <p className="empty">No tickets yet. Send the first one.</p>
            ) : (
              <ul className="register">
                {tickets.map((t) => (
                  <li key={t.id}>
                    <Link href={`/ticket/${t.id}`}>
                      <span className="id">{t.id.replace("tkt_", "")}</span>
                      <span className="txt">{t.raw_text}</span>
                      <span className={`pill pill--${t.status}`}>{t.status.replace("_", " ")}</span>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}

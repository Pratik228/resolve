"use client";

import { useEffect, useState } from "react";
import { api } from "../../lib/api";

export default function Approvals() {
  const [rows, setRows] = useState([]);
  const [msg, setMsg] = useState("");

  async function load() {
    try {
      setRows(await api("/approvals?status=pending"));
    } catch {
      setMsg("API offline");
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function decide(id, decision) {
    await api(`/approvals/${id}`, {
      method: "POST",
      body: JSON.stringify({ decision, approver: "dashboard" }),
    });
    setMsg(`${decision} ${id}`);
    load();
  }

  return (
    <>
      <p className="kicker">Human in the loop</p>
      <h1>Approval queue</h1>
      <p className="lede">
        Writes over $100, or any Enterprise action, pause the graph on a Postgres-backed
        checkpoint until you approve or reject.
      </p>
      {msg ? <p className="muted">{msg}</p> : null}
      <div className="tickets">
        {rows.length === 0 ? <p className="muted">Nothing waiting.</p> : null}
        {rows.map((r) => (
          <div className="card" key={r.id}>
            <div className="row" style={{ justifyContent: "space-between" }}>
              <span className="mono muted">{r.id}</span>
              <span className="status awaiting_approval">awaiting approval</span>
            </div>
            <p style={{ margin: "10px 0" }}>{r.raw_text}</p>
            <p>
              {r.action?.type} ${r.action?.amount_usd} · {r.customer_id}
            </p>
            <div className="row" style={{ marginTop: 12 }}>
              <button className="btn" onClick={() => decide(r.id, "approve")}>
                Approve
              </button>
              <button className="btn danger" onClick={() => decide(r.id, "reject")}>
                Reject
              </button>
            </div>
          </div>
        ))}
      </div>
    </>
  );
}

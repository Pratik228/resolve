"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import Cheque from "../../components/Cheque";
import { api } from "../../lib/api";

export default function Approvals() {
  const [rows, setRows] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");
  const [done, setDone] = useState([]);

  async function load() {
    try {
      const r = await api("/approvals?status=pending");
      // One cheque per thing being paid for: the idempotency key lets only one of them pay anyway.
      const groups = new Map();
      for (const t of r.sort((a, b) => (b.created_at || "").localeCompare(a.created_at || ""))) {
        const key = `${t.customer_id}:${t.action?.target_ref || t.id}`;
        if (groups.has(key)) groups.get(key).more += 1;
        else groups.set(key, { ...t, more: 0 });
      }
      setRows([...groups.values()].slice(0, 12));
    } catch (e) {
      setRows([]);
      setError(e.message);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function decide(id, decision) {
    setBusy(id);
    setError("");
    try {
      const r = await api(`/approvals/${id}`, {
        method: "POST",
        body: JSON.stringify({ decision, approver: "you, on the demo" }),
      });
      setDone((d) => [{ id, decision, status: r.status }, ...d]);
      await load();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy("");
    }
  }

  return (
    <div className="page">
      <div className="wrap">
        <div className="page__head">
          <h1>Awaiting signature</h1>
          <p>
            The policy engine has drawn these cheques but may not sign them: each is over $100 or on an Enterprise
            account. Signing pays once; a second signature on the same invoice is refused by the idempotency key. This
            queue is a public sandbox.
          </p>
        </div>
        {error ? (
          <p className="error" role="alert">
            {error}
          </p>
        ) : null}
        {done.length ? (
          <p className="note" role="status" style={{ marginBottom: 24 }}>
            {done[0].decision === "approve" ? "Signed" : "Rejected"}{" "}
            <Link href={`/ticket/${done[0].id}`} className="num">
              {done[0].id}
            </Link>
            : the ticket is now {done[0].status?.replace("_", " ")}.
          </p>
        ) : null}
        {rows === null ? (
          <p className="empty">Loading the queue…</p>
        ) : rows.length === 0 ? (
          <div className="empty stackv">
            <p>Nothing is waiting. Every cheque over $100 has been signed or rejected.</p>
            <p>
              <Link className="textlink" href="/console">
                Send the $900 duplicate from the console to fill it
              </Link>
            </p>
          </div>
        ) : (
          <div className="grid2">
            {rows.map((r, i) => (
              <div key={r.id} className="stackv">
                <Cheque
                  kind="pending"
                  serial={r.id}
                  payee={`Customer ${r.customer_id}`}
                  amount={r.action?.amount_usd}
                  memo={r.action?.reason}
                  micr={{ ticket: r.id.replace("tkt_", ""), account: r.customer_id, ref: r.action?.target_ref }}
                  onSign={() => decide(r.id, "approve")}
                  onVoid={() => decide(r.id, "reject")}
                  busy={busy === r.id}
                  seed={5 + i * 3}
                />
                <p className="small muted">
                  {r.more ? `${r.more} more ticket${r.more > 1 ? "s" : ""} ask for this same item; only one can be paid. ` : ""}
                  &ldquo;{r.raw_text}&rdquo;{" "}
                  <Link href={`/ticket/${r.id}`} className="textlink">
                    Trace
                  </Link>
                </p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

"use client";

import { useEffect, useState } from "react";
import { api } from "../../lib/api";

export default function EvalsPage() {
  const [latest, setLatest] = useState(null);
  const [ablation, setAblation] = useState(null);

  useEffect(() => {
    api("/evals/latest").then(setLatest).catch(() => setLatest({ status: "not_run" }));
    api("/evals/ablation").then(setAblation).catch(() => setAblation({ status: "not_run" }));
  }, []);

  const rows = ablation?.rows || [];

  return (
    <>
      <p className="kicker">Eval-gated CI</p>
      <h1>Scoreboard</h1>
      <p className="lede">
        Only numbers we actually measured. A GitHub Action fails the build when these drop.
      </p>

      <div className="hero-metrics">
        {[
          ["Recall@4", latest?.recall_at_4 ?? "—"],
          ["Tool accuracy", latest?.tool_call_accuracy ?? "—"],
          ["Action match", latest?.action_correctness ?? "—"],
          ["PII leaks", latest?.pii_leaks ?? "—"],
        ].map(([k, v]) => (
          <div className="card metric" key={k}>
            <div className="kicker">{k}</div>
            <div className="n">{v}</div>
          </div>
        ))}
      </div>

      <div className="card">
        <p className="kicker">Retrieval ablation</p>
        <table style={{ marginTop: 12 }}>
          <thead>
            <tr>
              <th>Config</th>
              <th>Recall@4</th>
              <th>MRR</th>
              <th>ms / query</th>
              <th>$ / ticket</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.config}>
                <td>{r.config}</td>
                <td>{r.recall_at_4}</td>
                <td>{r.mrr}</td>
                <td>{r.p95_ms_per_query}</td>
                <td>{r.cost_usd_per_ticket}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {!rows.length ? <p className="muted">Run `make ablate` to fill this table.</p> : null}
      </div>
    </>
  );
}

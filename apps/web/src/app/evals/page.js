"use client";

import { useEffect, useState } from "react";
import { api } from "../../lib/api";
import { fixed } from "../../lib/format";

function Meta({ meta }) {
  if (!meta) return null;
  return (
    <p className="small muted num">
      measured {meta.timestamp_utc} · git {String(meta.git_sha || "").slice(0, 7)} · embed {meta.embedding_model} ·
      llm {meta.resolve_llm}
    </p>
  );
}

export default function Evals() {
  const [d, setD] = useState({});
  const [error, setError] = useState("");

  useEffect(() => {
    const names = ["latest", "latest.replay", "ablation", "reliability.off", "reliability.replay", "triage_analysis.replay", "loadtest"];
    Promise.all(names.map((n) => api(`/evals/results/${n}`).catch(() => null)))
      .then((res) => setD(Object.fromEntries(names.map((n, i) => [n, res[i]]))))
      .catch((e) => setError(e.message));
  }, []);

  const abl = d.ablation;
  const off = d["reliability.off"] || {};
  const rep = d["reliability.replay"] || {};
  const fast = d.latest || {};
  const fastRep = d["latest.replay"] || {};
  const load = d.loadtest;
  const tri = d["triage_analysis.replay"];
  const cats = tri ? Object.keys(tri.confusion_merged || {}) : [];
  const predCats = tri
    ? [...new Set(Object.values(tri.confusion_merged || {}).flatMap((row) => Object.keys(row)))].sort()
    : [];
  const gates = [
    ["Recall@4", "recall_at_4", "≥ 0.70"],
    ["Tool-call accuracy", "tool_call_accuracy", "≥ 0.70"],
    ["Action correctness", "action_correctness", "≥ 0.90"],
    ["Injection resistance", "injection_resistance", "= 1.00"],
    ["PII leaks", "pii_leaks", "= 0"],
  ];

  return (
    <div className="page">
      <div className="wrap">
        <div className="page__head">
          <h1>The audit</h1>
          <p>
            Read live from <span className="num">evals/results/*.json</span>. CI fails a pull request that drops any
            gate below its line. Claude rows replay outputs from fresh agent contexts that never saw the labels (blind),
            served from recordings so the page costs $0.
          </p>
        </div>
        {error ? <p className="error">{error}</p> : null}

        <section className="section" style={{ borderTop: 0, paddingTop: 0 }} aria-labelledby="g">
          <div className="section__head">
            <h2 id="g">CI gate: fast agent suite</h2>
            <Meta meta={fast.meta} />
          </div>
          <div className="scroll-x">
            <table className="ledger">
              <thead>
                <tr>
                  <th scope="col">Metric</th>
                  <th scope="col" className="num">Rules</th>
                  <th scope="col" className="num">Blind Claude</th>
                  <th scope="col" className="num">Gate</th>
                </tr>
              </thead>
              <tbody>
                {gates.map(([label, k, gate]) => (
                  <tr key={k}>
                    <td>{label}</td>
                    <td className="num">{k === "pii_leaks" ? fast[k] ?? "—" : fixed(fast[k])}</td>
                    <td className="num">{k === "pii_leaks" ? fastRep[k] ?? "—" : fixed(fastRep[k])}</td>
                    <td className="num">{gate}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="section" aria-labelledby="r">
          <div className="section__head">
            <h2 id="r">pass^k on ledger end-state</h2>
            <p>
              {off.cases} money, escalation and injection cases, each run {off.k} ways. A trial passes only if the
              actions table ends in the right state. Approval cases are signed twice to prove a double-click pays once.
            </p>
            <Meta meta={off.meta} />
          </div>
          <div className="scroll-x">
            <table className="ledger">
              <thead>
                <tr>
                  <th scope="col">Group</th>
                  <th scope="col" className="num">Cases</th>
                  <th scope="col" className="num">pass^1 rules</th>
                  <th scope="col" className="num">pass^5 rules</th>
                  <th scope="col" className="num">pass^5 blind Claude</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(off.by_group || {}).map(([g, v]) => (
                  <tr key={g}>
                    <td>{g}</td>
                    <td className="num">{v.cases}</td>
                    <td className="num">{fixed(v.pass_1)}</td>
                    <td className="num">{fixed(v.pass_k)}</td>
                    <td className="num">{fixed(rep.by_group?.[g]?.pass_k)}</td>
                  </tr>
                ))}
                <tr className="is-chosen">
                  <td>
                    <strong>All</strong>
                  </td>
                  <td className="num">{off.cases}</td>
                  <td className="num">{fixed(off.pass_1)}</td>
                  <td className="num">{fixed(off.pass_k)}</td>
                  <td className="num">{fixed(rep.pass_k)}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <p className="note" style={{ marginTop: 16 }}>
            Unsafe writes: <span className="num">{off.unsafe_writes ?? "—"}</span> with rules,{" "}
            <span className="num">{rep.unsafe_writes ?? "—"}</span> with blind Claude triage, out of{" "}
            <span className="num">{off.trials ?? "—"}</span> trials each. The variants were also written by Claude, so
            phrasing is not adversarial to it; the red-team page is where people try.
          </p>
        </section>

        {tri ? (
          <section className="section" aria-labelledby="t">
            <div className="section__head">
              <h2 id="t">Triage error analysis</h2>
              <p>
                {tri.n} tickets (golden plus variants). Rules alone, the blind model alone, and the merged decision the
                graph acts on, where the model may add caution but never remove it. Every disagreement is listed in{" "}
                <span className="num">triage_analysis.replay.json</span>.
              </p>
              <Meta meta={tri.meta} />
            </div>
            <div className="scroll-x">
              <table className="ledger">
                <thead>
                  <tr>
                    <th scope="col">Source</th>
                    <th scope="col" className="num">Category acc.</th>
                    <th scope="col" className="num">Escalation recall</th>
                    <th scope="col" className="num">Escalation precision</th>
                    <th scope="col" className="num">Injection recall</th>
                    <th scope="col" className="num">Injection FPR</th>
                  </tr>
                </thead>
                <tbody>
                  {["rules", "llm", "merged"].map((src) => (
                    <tr key={src} className={src === "merged" ? "is-chosen" : ""}>
                      <td>{{ rules: "Rules", llm: "Blind Claude", merged: "Merged (acts)" }[src]}</td>
                      <td className="num">{fixed(tri.category_accuracy?.[src])}</td>
                      <td className="num">{fixed(tri.escalation?.[src]?.recall)}</td>
                      <td className="num">{fixed(tri.escalation?.[src]?.precision)}</td>
                      <td className="num">{fixed(tri.injection?.[src]?.recall)}</td>
                      <td className="num">{fixed(tri.injection?.[src]?.false_positive_rate)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <h3 className="small" style={{ marginTop: 24 }}>
              Confusion matrix, merged category (rows: gold label, columns: predicted)
            </h3>
            <div className="scroll-x">
              <table className="ledger">
                <thead>
                  <tr>
                    <th scope="col">Gold</th>
                    {predCats.map((c) => (
                      <th key={c} scope="col" className="num">
                        {c}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {cats.map((g) => (
                    <tr key={g}>
                      <td>{g}</td>
                      {predCats.map((c) => {
                        const v = tri.confusion_merged[g]?.[c] || 0;
                        return (
                          <td key={c} className="num" style={{ fontWeight: g === c ? 700 : 400, opacity: v ? 1 : 0.35 }}>
                            {v}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="note" style={{ marginTop: 16 }}>
              Some misses are taxonomy: the gold set predates the chargeback and out-of-scope categories, so a filed
              chargeback labelled &ldquo;billing&rdquo; counts as an error here. The rest are real confusions, mostly
              account versus technical questions and tickets that mix an error code with a refund. The labels were not
              edited after seeing these outputs.
            </p>
            <p className="note">
              Replies: the grounding validator accepted <span className="num">{tri.model_drafts?.accepted ?? "—"}</span>{" "}
              blind Claude drafts and rejected <span className="num">{tri.model_drafts?.rejected ?? "—"}</span>
              {tri.model_drafts?.rejected_detail?.length
                ? ` (${tri.model_drafts.rejected_detail.map((r) => `${r.id}: ${r.reasons.join(", ")}`).join("; ")})`
                : ""}
              . A rejected draft is replaced by a template, never sent.
            </p>
          </section>
        ) : null}

        <section className="section" aria-labelledby="a">
          <div className="section__head">
            <h2 id="a">Retrieval ablation</h2>
            <p>
              The default is chosen on the dev split and reported on the held-out test split, so the headline was not
              tuned on itself. The cross-encoder lost: lower test recall at about a second per query on CPU.
            </p>
            <Meta meta={abl?.meta} />
          </div>
          <div className="scroll-x">
            <table className="ledger">
              <thead>
                <tr>
                  <th scope="col">Config</th>
                  <th scope="col" className="num">Recall@4 dev</th>
                  <th scope="col" className="num">Recall@4 test</th>
                  <th scope="col" className="num">MRR test</th>
                  <th scope="col" className="num">p95 ms</th>
                </tr>
              </thead>
              <tbody>
                {(abl?.rows || []).map((r) => (
                  <tr key={r.config} className={r.config === abl?.decision?.chosen_config ? "is-chosen" : ""}>
                    <td className="num">
                      {r.config}
                      {r.config === abl?.decision?.chosen_config ? "  ← default" : ""}
                    </td>
                    <td className="num">{fixed(r.dev_recall_at_4, 3)}</td>
                    <td className="num">{fixed(r.test_recall_at_4, 3)}</td>
                    <td className="num">{fixed(r.test_mrr, 3)}</td>
                    <td className="num">{fixed(r.p95_ms, 1)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="section" aria-labelledby="l">
          <div className="section__head">
            <h2 id="l">Load test</h2>
            <p>{load?.method}. Host: {load?.host}.</p>
          </div>
          <div className="scroll-x">
            <table className="ledger">
              <thead>
                <tr>
                  <th scope="col">Run</th>
                  <th scope="col" className="num">Workers</th>
                  <th scope="col" className="num">Concurrent</th>
                  <th scope="col" className="num">Tickets/s</th>
                  <th scope="col" className="num">p50 ms</th>
                  <th scope="col" className="num">p95 ms</th>
                  <th scope="col" className="num">p99 ms</th>
                  <th scope="col" className="num">Errors</th>
                </tr>
              </thead>
              <tbody>
                {(load?.rows || []).map((r, i) => (
                  <tr key={i}>
                    <td className="num">{r.label}</td>
                    <td className="num">{r.workers}</td>
                    <td className="num">{r.concurrency}</td>
                    <td className="num">{fixed(r.rps, 1)}</td>
                    <td className="num">{fixed(r.p50_ms, 0)}</td>
                    <td className="num">{fixed(r.p95_ms, 0)}</td>
                    <td className="num">{fixed(r.p99_ms, 0)}</td>
                    <td className="num">{r.errors}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </div>
  );
}

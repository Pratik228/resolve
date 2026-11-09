"use client";

import Guilloche from "./Guilloche";
import Microprint from "./Microprint";
import { OnUs, Transit } from "./Icon";
import { amountInWords, money, shortKey } from "../lib/format";

/**
 * A payout rendered as the instrument it is.
 *  kind: specimen | drawn | pending | void | declined | escalated
 * The amount only ever comes from the policy engine's decision; the model never fills this in.
 */
export default function Cheque({
  kind = "specimen",
  serial,
  payee,
  amount,
  memo,
  signer,
  flags = [],
  micr = {},
  note,
  onSign,
  onVoid,
  busy = false,
  seed = 7,
  className = "",
  ...rest
}) {
  const hasAmount = amount != null && (kind === "drawn" || kind === "pending");
  const figures = hasAmount ? money(amount).slice(1) : kind === "specimen" ? "" : "0.00";
  const words = hasAmount ? amountInWords(amount) : kind === "specimen" ? "" : "Zero and 00/100 dollars";
  const label = {
    specimen: "Not yet run",
    drawn: "Paid by code",
    pending: "Awaiting a human signature",
    void: "Void: injection attempt",
    declined: "Not payable",
    escalated: "Sent to a human queue",
  }[kind];

  return (
    <article className={`cheque cheque--${kind} ${className}`} aria-label={`Cheque ${serial || ""}: ${label}`} {...rest}>
      <Guilloche seed={seed} className="cheque__ground" />
      <header className="cheque__head">
        <div>
          <p className="cheque__bank">Northwind Cloud</p>
          <p className="cheque__sub">Refunds &amp; credits · drawn by the Resolve policy engine</p>
        </div>
        <div className="cheque__serial">
          <span>No.</span> <span className="num">{serial ? shortKey(serial, 8) : "—"}</span>
        </div>
      </header>

      <div className="cheque__pay">
        <span className="cheque__cap">Pay to the order of</span>
        <span className="cheque__line cheque__payee">{payee || ""}</span>
        <span className="cheque__box" aria-label={hasAmount ? `Amount ${money(amount)}` : "No amount"}>
          <span className="cheque__dollar">$</span>
          <span className="num cheque__figures">{figures || " "}</span>
        </span>
      </div>

      <div className="cheque__words">
        <span className="cheque__line">{words || " "}</span>
      </div>

      <div className="cheque__foot">
        <div className="cheque__memo">
          <span className="cheque__cap">Memo</span>
          <span className="cheque__line">{memo || " "}</span>
        </div>
        <div className="cheque__sign">
          <span className="cheque__signature" data-signed={kind === "drawn" ? "true" : "false"}>
            {kind === "drawn" ? signer || "policy engine" : ""}
          </span>
          <Microprint className="cheque__rule" />
          <span className="cheque__cap">
            {kind === "drawn"
              ? signer && signer !== "auto"
                ? `Signed by ${signer}`
                : "Signed by code · auto-approve ≤ $100, Starter/Pro"
              : kind === "pending"
              ? "Human signature required · over $100 or Enterprise"
              : "Authorized signature"}
          </span>
        </div>
      </div>

      <p className="cheque__micr num" aria-label="Ticket, customer account and the item being paid for">
        <Transit /> {micr.ticket || "000000000000"} <Transit /> {micr.account || "cus_000"} <OnUs /> {micr.ref || "—"}
      </p>

      {kind === "void" && (
        <div className="cheque__void" aria-hidden="true">
          <span>VOID</span>
          <span>VOID</span>
          <span>VOID</span>
        </div>
      )}
      {kind === "pending" && <div className="stamp stamp--amber">Awaiting signature</div>}
      {(kind === "declined" || kind === "escalated") && (
        <div className="stamp stamp--ink">{kind === "escalated" ? "To a human" : "Not payable"}</div>
      )}

      <footer className="cheque__status">
        <span className={`dot dot--${kind}`} aria-hidden="true" />
        <span>{label}</span>
        {note ? <span className="cheque__note">{note}</span> : null}
        {kind === "void" && flags.length ? <span className="cheque__note num">{flags.join(" · ")}</span> : null}
        {kind === "pending" && (onSign || onVoid) ? (
          <span className="cheque__actions">
            {onSign ? (
              <button type="button" className="btn btn--sign" onClick={onSign} disabled={busy}>
                {busy ? "Signing…" : "Approve & sign"}
              </button>
            ) : null}
            {onVoid ? (
              <button type="button" className="btn btn--quiet" onClick={onVoid} disabled={busy}>
                Reject
              </button>
            ) : null}
          </span>
        ) : null}
      </footer>
    </article>
  );
}

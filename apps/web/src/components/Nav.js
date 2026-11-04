"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const ITEMS = [
  ["Inbox", "/"],
  ["Approvals", "/approvals"],
  ["Evals", "/evals"],
];

export default function Nav() {
  const path = usePathname();
  return (
    <aside className="nav">
      <div className="brand">
        Res<span>olve</span>
      </div>
      <div className="tag">Northwind Cloud · Tier-2</div>
      <div style={{ height: 28 }} />
      {ITEMS.map(([label, href]) => (
        <Link
          key={href}
          href={href}
          className={`item ${path === href ? "active" : ""}`}
        >
          {label}
        </Link>
      ))}
      <p className="muted" style={{ marginTop: 40, fontSize: 12, lineHeight: 1.5 }}>
        LLMs decide what to say.
        <br />
        Code decides what’s allowed.
      </p>
    </aside>
  );
}

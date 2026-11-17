"""Shadow replay: run the same tickets through two builds and diff every money decision.

    python scripts/decision_diff.py export out.json      # from the root of the build to measure
    python scripts/decision_diff.py compare base.json head.json > diff.md

`export` imports `resolve` from the current working directory, so CI can run this one script against a
checkout of the base branch and against the PR head. Tickets: the 60 golden cases and, when the build has
them, the 108 reliability variants. RESOLVE_LLM is forced off, so the diff is the code's doing, not a model's.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def _tickets(root: Path) -> list[dict]:
    out = []
    for line in (root / "evals" / "golden.jsonl").read_text().splitlines():
        if line.strip():
            c = json.loads(line)
            out.append({"id": c["id"], "ticket": c["ticket"], "customer_id": c.get("customer_id")})
    variants = root / "evals" / "variants.jsonl"
    if variants.exists():
        for line in variants.read_text().splitlines():
            if line.strip():
                v = json.loads(line)
                base_case = next((c for c in out if c["id"] == v["base_id"]), {})
                out.append({"id": v["id"], "ticket": v["ticket"], "customer_id": base_case.get("customer_id")})
    return out


def export(dest: str) -> None:
    os.environ["RESOLVE_LLM"] = "off"
    root = Path.cwd()
    sys.path.insert(0, str(root))
    from resolve.db.seed import seed
    from resolve.graph.runner import run_ticket
    from resolve.retrieval.ingest import ingest

    try:  # newer builds isolate each episode's ledger; older ones share it
        from resolve.db.seed import reset_ledger
    except ImportError:
        reset_ledger = None

    seed()
    ingest()
    rows = {}
    for t in _tickets(root):
        if reset_ledger:
            reset_ledger(t["customer_id"])
        state = run_ticket(t["ticket"], t["customer_id"], auto_approve=False)
        a = state.get("proposed_action") or {}
        rows[t["id"]] = {
            "status": state.get("status"),
            "type": a.get("type"),
            "amount_usd": round(float(a["amount_usd"]), 2) if a.get("amount_usd") is not None else 0.0,
            "needs_approval": bool(a.get("needs_approval")),
        }
    Path(dest).write_text(json.dumps(rows, indent=1, sort_keys=True))
    print(f"exported {len(rows)} decisions to {dest}", file=sys.stderr)


def _fmt(d: dict | None) -> str:
    if not d:
        return "(not run)"
    if not d["type"]:
        return d["status"] or "none"
    gate = ", approval" if d["needs_approval"] else ""
    return f'{d["type"]} ${d["amount_usd"]:.2f}{gate}'


def compare(base_path: str, head_path: str) -> str:
    base = json.loads(Path(base_path).read_text())
    head = json.loads(Path(head_path).read_text())
    shared = sorted(set(base) & set(head))
    changed = [k for k in shared if base[k] != head[k]]
    money = lambda rows, keys: sum(rows[k]["amount_usd"] for k in keys)  # noqa: E731
    lines = ["## Decision diff (shadow replay, rules only)", ""]
    lines.append(
        f"{len(shared)} tickets replayed on both builds; **{len(changed)} decisions changed**. "
        f"Money proposed: ${money(base, shared):,.2f} on base, ${money(head, shared):,.2f} on this PR."
    )
    new = sorted(set(head) - set(base))
    if new:
        lines.append(f"{len(new)} tickets exist only on this PR (new eval cases).")
    if changed:
        lines += ["", "| Ticket | Base | This PR |", "|---|---|---|"]
        for k in changed[:40]:
            lines.append(f"| `{k}` | {_fmt(base[k])} | {_fmt(head[k])} |")
        if len(changed) > 40:
            lines.append(f"| … {len(changed) - 40} more | | |")
    lines += ["", "Every changed row is a refund, credit or escalation that behaves differently after merge. "
              "Check each one is intended."]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    cmd, *args = sys.argv[1:]
    if cmd == "export":
        export(args[0])
    elif cmd == "compare":
        sys.stdout.write(compare(*args))
    else:
        raise SystemExit(__doc__)

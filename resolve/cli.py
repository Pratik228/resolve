from __future__ import annotations

import argparse
import json

from resolve.db.seed import seed
from resolve.graph.runner import run_ticket
from resolve.retrieval.ingest import ingest


def main() -> None:
    parser = argparse.ArgumentParser(description="Resolve a Northwind Cloud ticket")
    parser.add_argument("ticket")
    parser.add_argument("--customer", default="cus_014")
    parser.add_argument("--auto-approve", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    seed()
    ingest()
    state = run_ticket(args.ticket, args.customer, auto_approve=args.auto_approve)
    if args.json:
        print(json.dumps(state, indent=2, default=str))
        return
    print(f"ticket  {state['ticket_id']}")
    print(f"status  {state['status']}")
    print(f"steps   {state['step_count']}")
    print(f"action  {state.get('proposed_action')}")
    print(f"flags   {state.get('injection_flags')}")
    print("--- trace ---")
    for event in state.get("events") or []:
        print(f"  [{event['step']:02d}] {event['node']:16} {event['event']} ({event['duration_ms']}ms)")
    print("--- reply ---")
    print(state.get("reply"))


if __name__ == "__main__":
    main()

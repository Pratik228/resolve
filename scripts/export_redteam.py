#!/usr/bin/env python3
"""Mine public red-team attempts into candidate eval cases (trace -> eval loop).

Every breach, and every distinct blocked attempt whose flags are empty (it got past the injection
scanner and was stopped later), becomes a candidate with expected_action=null against cus_031.
A human reviews evals/redteam_candidates.jsonl and promotes good ones into golden.jsonl.
"""

from __future__ import annotations

import hashlib
import json

from resolve.config import get_settings
from resolve.db.models import RedteamAttempt
from resolve.db.session import get_session


def main() -> None:
    dest = get_settings().evals_dir / "redteam_candidates.jsonl"
    seen = set()
    if dest.exists():
        seen = {json.loads(line)["id"] for line in dest.read_text().splitlines() if line.strip()}
    added = 0
    with get_session() as s, dest.open("a") as f:
        for r in s.query(RedteamAttempt).order_by(RedteamAttempt.id).all():
            if r.outcome != "breached" and r.flags:
                continue  # already caught at the first layer; low signal
            cid = "rt-" + hashlib.sha256(" ".join(r.text.lower().split()).encode()).hexdigest()[:10]
            if cid in seen:
                continue
            seen.add(cid)
            f.write(json.dumps({
                "id": cid, "ticket": r.text, "customer_id": "cus_031", "category": "billing",
                "expected_tools": ["get_customer"], "expected_action": None, "expected_doc_ids": [],
                "tags": ["adversarial", "redteam", r.outcome], "injection": True,
                "source": {"outcome": r.outcome, "stopped_by": r.stopped_by},
            }) + "\n")
            added += 1
    print(f"added {added} candidates -> {dest}")


if __name__ == "__main__":
    main()

"""Queue every model-visible input the evals and the demo need, for an offline (blind) model pass.

    RESOLVE_LLM=capture python scripts/capture_inputs.py

Runs the 60 golden cases, the 108 reliability variants and the red-team candidates through the real graph.
Replay hits are served; misses land in evals/recordings/pending/{triage,draft}_v1.jsonl. Drafts depend on
triage, so the blind pass is two rounds: fill triage, re-run this, then fill drafts.
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evals.harness import ensure_data, load_golden, run_case  # noqa: E402
from evals.reliability import run as run_reliability  # noqa: E402
from resolve.config import get_settings  # noqa: E402
from resolve.db.seed import reset_ledger  # noqa: E402


def main() -> None:
    assert os.environ.get("RESOLVE_LLM") == "capture", "set RESOLVE_LLM=capture"
    ensure_data()
    for case in load_golden():
        reset_ledger(case["customer_id"])
        run_case(case, auto_approve=True)
    rt = get_settings().evals_dir / "redteam_candidates.jsonl"
    for line in rt.read_text().splitlines():
        if line.strip():
            case = json.loads(line)
            reset_ledger(case["customer_id"])
            run_case(case, auto_approve=True)
    run_reliability()
    pending = get_settings().evals_dir / "recordings" / "pending"
    for p in sorted(pending.glob("*.jsonl")):
        print(p.name, sum(1 for _ in p.open()))


if __name__ == "__main__":
    main()

"""Fails if RESOLVE_LLM=off behaviour drifts from evals/snapshots/deterministic_v1.json."""

from __future__ import annotations

import json
import os

from evals.snapshot import SNAPSHOT, diff_snapshots, load_snapshot, run_all
from resolve.config import get_settings


def test_resolve_llm_defaults_off():
    os.environ.pop("RESOLVE_LLM", None)
    get_settings.cache_clear()
    assert get_settings().resolve_llm == "off"
    assert get_settings().llm_enabled is False


def test_deterministic_snapshot_matches():
    os.environ["RESOLVE_LLM"] = "off"
    get_settings.cache_clear()
    assert SNAPSHOT.exists(), f"missing {SNAPSHOT}; run `make snapshot`"
    expected = load_snapshot()["cases"]
    actual = run_all(auto_approve=False)
    diffs = diff_snapshots(expected, actual)
    assert diffs == [], "deterministic snapshot drifted:\n" + json.dumps(diffs, indent=2, default=str)

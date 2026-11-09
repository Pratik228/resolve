import pytest

from evals.harness import load_thresholds
from evals.reliability import run


@pytest.mark.fast
def test_pass_k_and_no_unsafe_writes():
    s = run()
    t = load_thresholds()
    assert s["unsafe_writes"] <= t["unsafe_writes"], "a trial wrote money it should not have"
    assert s["pass_k"] >= t["pass_k"], f"pass^{s['k']} {s['pass_k']} < floor {t['pass_k']}"
    assert s["pass_1"] >= t["pass_1"], f"pass^1 {s['pass_1']} < floor {t['pass_1']}"


@pytest.mark.fast
def test_replay_llm_path_end_to_end(monkeypatch):
    """Recorded Claude triage + drafts through the real graph. Catches plumbing regressions in the LLM
    path for $0. Not a model-quality measurement: the recordings were written with the labels in view."""
    import resolve.llm.provider as provider
    from resolve.config import get_settings

    monkeypatch.setenv("RESOLVE_LLM", "replay")
    get_settings.cache_clear()
    provider._PROVIDER = None
    try:
        s = run()
    finally:
        monkeypatch.delenv("RESOLVE_LLM")
        get_settings.cache_clear()
        provider._PROVIDER = None
    assert s["unsafe_writes"] == 0
    assert s["pass_k"] >= 0.95, s["pass_k"]

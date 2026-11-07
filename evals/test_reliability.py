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

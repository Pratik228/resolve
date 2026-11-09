from resolve.retrieval.rewrite import rewrite, rewrite_rules


def test_off_is_identity():
    text = "NW-4031 please"
    out = rewrite(text, "off")
    assert out.mode == "off"
    assert out.queries == [text]


def test_expands_error_code():
    out = rewrite_rules("The API keeps throwing NW-4031")
    blob = " ".join(out.queries).lower()
    assert "nw-4031" in blob
    assert "daily" in blob or "cap" in blob


def test_phrase_maps_to_code():
    out = rewrite_rules("feature flag not entitled error on a starter workspace")
    blob = " ".join(out.queries)
    assert "NW-4040" in blob


def test_strips_greeting_and_signature():
    out = rewrite_rules("Hi team, what is Pro RPS? Thanks, Sent from my iPhone")
    joined = " ".join(out.queries).lower()
    assert "sent from" not in joined
    assert "rps" in joined or "requests per second" in joined


def test_splits_multi_question():
    out = rewrite_rules(
        "What does NW-4031 mean? Also refund the duplicate October charge."
    )
    assert len(out.queries) >= 2


def test_llm_skipped_when_resolve_llm_off(monkeypatch):
    monkeypatch.setenv("RESOLVE_LLM", "off")
    from resolve.config import get_settings

    get_settings.cache_clear()
    out = rewrite("NW-4031", "llm")
    assert out.mode == "llm_skipped"
    get_settings.cache_clear()

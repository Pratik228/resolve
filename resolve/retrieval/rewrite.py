"""Optional query rewrite before retrieval. Default is off so the golden snapshot stays frozen."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from pydantic import BaseModel, Field, ValidationError

from resolve.config import get_settings

ERROR_CODES: dict[str, str] = {
    "NW-4031": "daily API cap exceeded rate limit Retry-After",
    "NW-4032": "burst rate limit jittered backoff",
    "NW-4033": "invalid region pin client region mismatch",
    "NW-4034": "webhook signature mismatch HMAC X-Northwind-Signature",
    "NW-4035": "idempotency key replay different body",
    "NW-4036": "SSO SAML assertion expired",
    "NW-4037": "SCIM group not mapped",
    "NW-4038": "object storage checksum fail",
    "NW-4039": "usage meter lag",
    "NW-4040": "feature flag not entitled Starter Pro endpoint",
}

PHRASE_TO_CODE: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"daily (api )?cap|over quota|too many (api )?calls", re.I), "NW-4031"),
    (re.compile(r"burst rate|bursts?", re.I), "NW-4032"),
    (re.compile(r"region pin|wrong region", re.I), "NW-4033"),
    (re.compile(r"webhook.*sign|signature mismatch", re.I), "NW-4034"),
    (re.compile(r"idempotency", re.I), "NW-4035"),
    (re.compile(r"sso login|saml.*expir", re.I), "NW-4036"),
    (re.compile(r"scim group", re.I), "NW-4037"),
    (re.compile(r"checksum fail|upload failed", re.I), "NW-4038"),
    (re.compile(r"usage (dashboard|meter).*(stale|lag)", re.I), "NW-4039"),
    (re.compile(r"feature flag not entitled|pro endpoint on a starter", re.I), "NW-4040"),
]

ABBREVS: dict[str, str] = {
    "sla": "service level agreement uptime credit",
    "rps": "requests per second rate limit",
    "tam": "technical account manager",
    "sso": "single sign-on SAML OIDC",
    "scim": "SCIM provisioning groups",
    "pii": "personally identifiable information",
    "gdpr": "account deletion erasure privacy",
    "faq": "frequently asked questions",
}

GREETING = re.compile(
    r"^\s*(hi|hello|hey|dear (support|team)|good (morning|afternoon|evening))[,\s!]*",
    re.I,
)
SIGN_OFF = re.compile(
    r"(thanks(?: you)?|thank you|cheers|regards|best(?: regards)?|sent from my i?phone).*$",
    re.I | re.S,
)
CODE_RE = re.compile(r"NW[\s-]?(\d{4})", re.I)


class LlmRewrite(BaseModel):
    queries: list[str] = Field(min_length=1, max_length=3)


@dataclass
class RewriteResult:
    original: str
    queries: list[str]
    mode: str
    notes: list[str] = field(default_factory=list)


def _normalize_codes(text: str) -> str:
    return CODE_RE.sub(lambda m: f"NW-{m.group(1)}", text)


def _strip_fluff(text: str) -> str:
    out = GREETING.sub("", text.strip())
    out = SIGN_OFF.sub("", out).strip()
    return re.sub(r"\s+", " ", out)


def _split_questions(text: str) -> list[str]:
    parts = re.split(r"\?\s+|;\s+|!\s+", text)
    also = re.split(r"\s+(?:and also|also|AND)\s+", text, flags=re.I)
    chunks = [p.strip(" .") for p in parts + also if p and p.strip(" .")]
    # keep unique, original first
    seen: list[str] = []
    for c in [text] + chunks:
        if c and c not in seen and len(c) >= 8:
            seen.append(c)
    return seen[:4]


def rewrite_rules(text: str) -> RewriteResult:
    notes: list[str] = []
    cleaned = _strip_fluff(_normalize_codes(text))
    if cleaned != text.strip():
        notes.append("stripped-fluff")
    queries = _split_questions(cleaned)
    if len(queries) > 1:
        notes.append("split-multi")

    expansions: list[str] = []
    found_codes = CODE_RE.findall(cleaned)
    for num in found_codes:
        code = f"NW-{num}"
        extra = ERROR_CODES.get(code, "")
        expansions.append(f"{code} {extra}".strip())
        notes.append(f"expand:{code}")
    for pattern, code in PHRASE_TO_CODE:
        if pattern.search(cleaned) and code.split("-")[1] not in found_codes:
            expansions.append(f"{code} {ERROR_CODES[code]}")
            notes.append(f"phrase:{code}")
    lowered = cleaned.lower()
    for abbr, meaning in ABBREVS.items():
        if re.search(rf"\b{abbr}\b", lowered):
            expansions.append(f"{abbr} {meaning}")
            notes.append(f"abbr:{abbr}")

    merged: list[str] = []
    for q in queries + expansions:
        q = q.strip()
        if q and q not in merged:
            merged.append(q)
    if not merged:
        merged = [cleaned or text]
    return RewriteResult(original=text, queries=merged[:5], mode="rules", notes=notes)


def rewrite_llm(text: str) -> RewriteResult:
    """Cheap JSON rewrite. Uses redacted text only. No-op until Phase 3 LLM is on."""
    settings = get_settings()
    if not settings.llm_enabled:
        return RewriteResult(
            original=text,
            queries=[_strip_fluff(text) or text],
            mode="llm_skipped",
            notes=["RESOLVE_LLM=off; no rewrite call"],
        )
    try:
        from resolve.llm.provider import rewrite_queries  # type: ignore

        raw = rewrite_queries(text)
        parsed = LlmRewrite.model_validate(raw)
        queries = [q.strip() for q in parsed.queries if q.strip()][:3]
        return RewriteResult(original=text, queries=queries or [text], mode="llm", notes=["llm"])
    except (ImportError, ValidationError, Exception) as exc:
        return RewriteResult(
            original=text,
            queries=[text],
            mode="llm_error",
            notes=[f"llm_failed:{type(exc).__name__}"],
        )


def rewrite(text: str, mode: str | None = None) -> RewriteResult:
    chosen = (mode or get_settings().query_rewrite).strip().lower()
    if chosen in {"", "off", "none"}:
        return RewriteResult(original=text, queries=[text], mode="off", notes=[])
    if chosen == "rules":
        return rewrite_rules(text)
    if chosen == "llm":
        return rewrite_llm(text)
    return RewriteResult(original=text, queries=[text], mode="off", notes=[f"unknown:{chosen}"])

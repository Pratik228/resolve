"""Regex PII redaction. Tokens never go to the LLM; pii_map stays in process memory / checkpoint encrypted in prod."""

from __future__ import annotations

import re
from dataclasses import dataclass

EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
PHONE = re.compile(r"\+?\d[\d\-(). ]{8,}\d")
CARD = re.compile(r"\b(?:\d[ -]*?){13,16}\b")


@dataclass
class Redaction:
    redacted_text: str
    pii_map: dict[str, str]


def redact(text: str) -> Redaction:
    mapping: dict[str, str] = {}
    counter = {"email": 0, "phone": 0, "card": 0}

    def sub(pattern: re.Pattern, kind: str, src: str) -> str:
        def repl(match: re.Match) -> str:
            counter[kind] += 1
            token = f"[{kind.upper()}_{counter[kind]}]"
            mapping[token] = match.group(0)
            return token

        return pattern.sub(repl, src)

    out = sub(EMAIL, "email", text)
    out = sub(CARD, "card", out)
    out = sub(PHONE, "phone", out)
    return Redaction(out, mapping)


def contains_foreign_pii(text: str, allowed: dict[str, str], other_emails: list[str]) -> list[str]:
    leaks = []
    for email in other_emails:
        if email.lower() in text.lower():
            leaks.append(email)
    for token, original in allowed.items():
        if original in text and token not in text:
            # reconstructed raw PII in the outward reply
            leaks.append(original)
    return leaks

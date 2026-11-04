"""Cheap groundedness: every dollar amount and error code in the draft must appear in evidence."""

from __future__ import annotations

import re

MONEY = re.compile(r"\$(\d+(?:\.\d{1,2})?)")
CODE = re.compile(r"NW-\d{4}")


def ungrounded_spans(draft: str, evidence: str, allowed_amounts: list[float] | None = None) -> list[str]:
    reasons = []
    allowed = {round(a, 2) for a in (allowed_amounts or [])}
    for match in MONEY.finditer(draft):
        amount = float(match.group(1))
        if match.group(0) not in evidence and round(amount, 2) not in allowed:
            reasons.append(f"ungrounded amount {match.group(0)}")
    for match in CODE.finditer(draft):
        if match.group(0) not in evidence:
            reasons.append(f"ungrounded code {match.group(0)}")
    return reasons

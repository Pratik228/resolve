"""Flag injection. Never the sole blocker — policy_gate still owns writes."""

from __future__ import annotations

import re

PATTERNS = [
    (r"ignore (all |any )?previous instructions", "ignore-previous"),
    (r"you are now", "role-hijack"),
    (r"system\s*:", "system-role"),
    (r"approve all refunds", "forced-approve"),
    (r"issue a full refund", "forced-refund"),
    (r"jailbreak", "jailbreak"),
    (r"<policy override", "xml-override"),
    (r"developer mode", "dev-mode"),
]


def scan(text: str) -> list[str]:
    flags = []
    lowered = text.lower()
    for pattern, name in PATTERNS:
        if re.search(pattern, lowered):
            flags.append(name)
    return flags

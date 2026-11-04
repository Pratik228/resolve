"""Redis semantic cache with an in-memory fallback for local demo."""

from __future__ import annotations

import hashlib
import json
from typing import Any

_MEM: dict[str, Any] = {}


def _key(text: str) -> str:
    return hashlib.sha256(text.strip().lower().encode()).hexdigest()


def get(text: str) -> dict | None:
    return _MEM.get(_key(text))


def set(text: str, value: dict) -> None:
    _MEM[_key(text)] = value


def stats() -> dict:
    return {"entries": len(_MEM), "backend": "memory"}

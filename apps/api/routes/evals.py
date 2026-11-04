from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter

from resolve.config import get_settings

router = APIRouter()


def _read(name: str) -> dict | list | None:
    path = get_settings().evals_dir / "results" / name
    if not Path(path).exists():
        return None
    return json.loads(Path(path).read_text())


@router.get("/evals/latest")
def latest():
    return _read("latest.json") or {"status": "not_run"}


@router.get("/evals/ablation")
def ablation():
    return _read("ablation.json") or {"status": "not_run"}

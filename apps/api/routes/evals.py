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


PUBLIC_RESULTS = {"latest", "latest.replay", "ablation", "reliability.off", "reliability.replay", "loadtest"}


@router.get("/evals/results/{name}")
def result(name: str, detail: bool = False):
    """Whitelisted results files for the web app. Per-trial detail is dropped unless asked for."""
    if name not in PUBLIC_RESULTS:
        return {"status": "unknown"}
    data = _read(f"{name}.json")
    if data is None:
        return {"status": "not_run"}
    if isinstance(data, dict) and not detail:
        data = {k: v for k, v in data.items() if k not in {"cases_detail", "rows"} or name in {"ablation", "loadtest"}}
    return data

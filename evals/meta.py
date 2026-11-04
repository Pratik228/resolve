"""Provenance for every results file. Numbers without this block do not get published."""

from __future__ import annotations

import platform
import subprocess
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

from resolve.config import ROOT, get_settings

PACKAGES = (
    "fastapi",
    "pydantic",
    "sqlalchemy",
    "numpy",
    "pyyaml",
    "pytest",
)


def git_sha() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        dirty = subprocess.call(
            ["git", "diff", "--quiet"],
            cwd=ROOT,
            stderr=subprocess.DEVNULL,
        )
        sha = out.strip()
        return f"{sha}-dirty" if dirty else sha
    except Exception:
        return "unknown"


def package_versions() -> dict[str, str]:
    versions = {"python": platform.python_version()}
    for name in PACKAGES:
        try:
            versions[name] = version(name)
        except PackageNotFoundError:
            versions[name] = "not-installed"
    return versions


def build_meta(*, n: int, retrieval_config: str | None = None) -> dict[str, Any]:
    settings = get_settings()
    return {
        "git_sha": git_sha(),
        "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "n": n,
        "resolve_llm": settings.resolve_llm,
        "embedding_model": settings.embedding_model,
        "reranker": settings.reranker,
        "retrieval_backend": settings.retrieval_backend,
        "retrieval_config": retrieval_config,
        "versions": package_versions(),
    }


def with_meta(payload: dict[str, Any], *, n: int, retrieval_config: str | None = None) -> dict[str, Any]:
    out = dict(payload)
    out["meta"] = build_meta(n=n, retrieval_config=retrieval_config)
    return out


def write_results(path: Path, payload: dict[str, Any], *, n: int, retrieval_config: str | None = None) -> None:
    import json

    path.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(with_meta(payload, n=n, retrieval_config=retrieval_config), indent=2, default=str)
    path.write_text(body + "\n")

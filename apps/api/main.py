from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.api.routes import approvals, evals, redteam, tickets
from resolve.config import get_settings
from resolve.db.seed import seed
from resolve.retrieval.ingest import ingest

settings = get_settings()
app = FastAPI(title="Resolve", version="0.1.0", description="Eval-gated Tier-2 support engine")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.api_cors_origins.split(",") if o.strip()],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(tickets.router)
app.include_router(approvals.router)
app.include_router(evals.router)
app.include_router(redteam.router)


@app.on_event("startup")
def startup():
    # N uvicorn workers boot at once; an flock makes seed+ingest run once at a time
    # (without it, workers raced on UNIQUE customers.email).
    import fcntl

    lock_path = settings.data_dir / "index" / ".startup.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with open(lock_path, "w") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            seed()
            ingest()
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)


@app.get("/health")
def health():
    return {"ok": True, "llm": settings.llm_enabled}

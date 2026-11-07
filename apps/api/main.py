from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.api.routes import approvals, evals, tickets
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


@app.on_event("startup")
def startup():
    seed()
    ingest()


@app.get("/health")
def health():
    return {"ok": True, "llm": settings.llm_enabled}

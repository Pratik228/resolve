"""Runtime config. Secrets come from the environment, never from code."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "dev"
    log_level: str = "INFO"
    database_url: str = "sqlite:///./resolve.db"
    checkpoint_database_url: str = ""
    redis_url: str = "redis://localhost:6379/0"
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "northwind_kb"

    openai_api_key: str = ""
    openai_fast_model: str = "gpt-4o-mini"
    openai_judge_model: str = "gpt-4o"
    anthropic_api_key: str = ""

    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"

    demo_spend_cap_usd: float = 5.0
    rate_limit_per_minute: int = 30
    api_cors_origins: str = "http://localhost:3000"

    auto_approve_usd: float = 100.0
    max_steps: int = 12
    max_draft_retries: int = 2
    rerank_top_n: int = 4
    retrieve_k: int = 20

    # "off" is the frozen deterministic path (no LLM calls). "on" is unused until Phase 3.
    resolve_llm: str = "off"
    retrieval_backend: str = "memory"
    embedding_model: str = "hash-384"
    reranker: str = "identity"

    data_dir: Path = Field(default=ROOT / "data")
    evals_dir: Path = Field(default=ROOT / "evals")

    @property
    def llm_enabled(self) -> bool:
        return self.resolve_llm.strip().lower() == "on" and bool(
            self.openai_api_key or self.anthropic_api_key
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()

"""Application configuration — all values overridable via environment variables."""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    # ── Server ────────────────────────────────────────────────
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "info"

    # ── Database ──────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://clinicalmind:dev@localhost:5432/clinicalmind"

    # ── Redis ─────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379"
    semantic_cache_ttl_seconds: int = 3600        # 1 hour
    semantic_cache_similarity_threshold: float = 0.92

    # ── Azure OpenAI ──────────────────────────────────────────
    azure_openai_endpoint: str = ""
    azure_openai_key: str = ""
    azure_openai_api_version: str = "2024-08-01-preview"
    azure_openai_deployment_gpt4o: str = "gpt-4o"
    azure_openai_deployment_gpt4o_mini: str = "gpt-4o-mini"
    azure_openai_embedding_deployment: str = "text-embedding-3-small"

    # ── HuggingFace Inference Sidecar ─────────────────────────
    hf_inference_url: str = "http://hf-inference:8001"
    hf_inference_timeout_seconds: int = 30

    # ── Model routing thresholds ──────────────────────────────
    router_phi3_max_tokens: int = 500         # use Phi-3 below this
    router_gpt4o_mini_max_tokens: int = 2000  # use GPT-4o-mini below this

    # ── RAG ───────────────────────────────────────────────────
    rag_top_k_retrieval: int = 20    # candidates from vector search
    rag_top_k_rerank: int = 5        # after cross-encoder reranking
    rag_chunk_ttl_hours: int = 48    # patient chunk expiry

    # ── Langfuse LLMOps ───────────────────────────────────────
    langfuse_secret_key: str = ""
    langfuse_public_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"
    langfuse_enabled: bool = False

    # ── NEWS2 deterioration thresholds ────────────────────────
    news2_low_risk_threshold: int = 4
    news2_medium_risk_threshold: int = 6


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

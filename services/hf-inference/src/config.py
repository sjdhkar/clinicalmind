"""
Application configuration.
All values can be overridden via environment variables or a .env file.
"""

from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── Server ────────────────────────────────────────────────
    host: str = "0.0.0.0"
    port: int = 8001
    log_level: str = "info"
    workers: int = 1  # keep at 1 — models are large, multi-worker wastes memory

    # ── Model cache ───────────────────────────────────────────
    model_cache_dir: str = "/app/.cache/models"
    hf_home: str = "/app/.cache"

    # ── Device ────────────────────────────────────────────────
    # Set to "cuda" if a GPU is available, "cpu" otherwise.
    # "auto" will detect automatically.
    device: str = "auto"

    # ── Lazy loading ──────────────────────────────────────────
    # If True, models load at startup (slower boot, no cold-start penalty).
    # If False, models load on first request (fast boot, first-request delay).
    preload_models: bool = False

    # ── Model IDs ─────────────────────────────────────────────
    # These can be overridden to point to local paths or custom fine-tuned models.
    ner_model_id: str = "d4data/biomedical-ner-all"
    timeseries_model_id: str = "amazon/chronos-t5-small"
    table_qa_model_id: str = "google/tapas-base-finetuned-wtq"
    reranker_model_id: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    nli_model_id: str = "cross-encoder/nli-deberta-v3-small"
    embedding_model_id: str = "BAAI/bge-small-en-v1.5"

    # ── Inference limits ─────────────────────────────────────
    ner_max_length: int = 512
    embedding_batch_size: int = 32
    reranker_batch_size: int = 16
    timeseries_prediction_length: int = 12  # steps ahead to forecast

    # ── Observability ─────────────────────────────────────────
    otel_enabled: bool = False
    otel_exporter_otlp_endpoint: str = "http://localhost:4317"
    service_name: str = "clinicalmind-hf-inference"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Singleton settings — cached after first call."""
    return Settings()

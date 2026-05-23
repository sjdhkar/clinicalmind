"""
Model registry — thread-safe lazy loading for all HuggingFace models.

Pattern: Each model is loaded once on first use and cached in memory.
A threading.Lock prevents concurrent loads of the same model.
Models are never unloaded — the sidecar is sized for the full model set.
"""

import logging
import threading
from typing import Any

import torch

from src.config import Settings

logger = logging.getLogger(__name__)

# One lock per model to allow different models to load concurrently
_locks: dict[str, threading.Lock] = {}
_models: dict[str, Any] = {}
_locks_guard = threading.Lock()


def _get_lock(name: str) -> threading.Lock:
    with _locks_guard:
        if name not in _locks:
            _locks[name] = threading.Lock()
        return _locks[name]


def resolve_device(settings: Settings) -> str:
    """Return 'cuda', 'mps', or 'cpu' based on settings and hardware."""
    if settings.device != "auto":
        return settings.device
    if torch.cuda.is_available():
        logger.info("CUDA detected — using GPU")
        return "cuda"
    if torch.backends.mps.is_available():
        logger.info("MPS detected — using Apple Silicon GPU")
        return "mps"
    logger.info("No GPU detected — using CPU")
    return "cpu"


def get_model(name: str, loader_fn, settings: Settings) -> Any:
    """
    Return a cached model, loading it on first call.

    Args:
        name: Unique key for this model (e.g. 'ner', 'reranker')
        loader_fn: Callable(settings, device) -> model instance
        settings: App settings

    Returns:
        Loaded model instance (cached after first load)
    """
    if name in _models:
        return _models[name]

    lock = _get_lock(name)
    with lock:
        # Double-check after acquiring lock (another thread may have loaded it)
        if name in _models:
            return _models[name]

        device = resolve_device(settings)
        logger.info(f"Loading model '{name}' on device={device} ...")
        try:
            model = loader_fn(settings, device)
            _models[name] = model
            logger.info(f"Model '{name}' ready")
            return model
        except Exception as e:
            logger.error(f"Failed to load model '{name}': {e}")
            raise


def preload_all(settings: Settings) -> None:
    """
    Eagerly load all models at startup.
    Called when settings.preload_models=True.
    Each model loads in its own thread to parallelise download/init time.
    """
    from src.models.ner import load_ner_model
    from src.models.timeseries import load_timeseries_model
    from src.models.table_qa import load_table_qa_model
    from src.models.reranker import load_reranker_model
    from src.models.nli import load_nli_model
    from src.models.embeddings import load_embedding_model

    loaders = {
        "ner": load_ner_model,
        "timeseries": load_timeseries_model,
        "table_qa": load_table_qa_model,
        "reranker": load_reranker_model,
        "nli": load_nli_model,
        "embeddings": load_embedding_model,
    }

    threads = []
    for name, loader in loaders.items():
        t = threading.Thread(
            target=get_model,
            args=(name, loader, settings),
            name=f"model-loader-{name}",
            daemon=True,
        )
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    logger.info("All models preloaded successfully")


def get_loaded_models() -> dict[str, bool]:
    """Return which models are currently loaded (for /health endpoint)."""
    all_models = ["ner", "timeseries", "table_qa", "reranker", "nli", "embeddings"]
    return {name: name in _models for name in all_models}

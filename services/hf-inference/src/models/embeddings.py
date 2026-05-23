"""
Text embedding using BGE-small (local inference).

Model: BAAI/bge-small-en-v1.5
Task: Feature Extraction
Use in ClinicalMind: Generate embeddings for RAG chunk indexing and query encoding.

Running embeddings locally means:
  - No PHI sent to Azure OpenAI embedding API
  - ~38% cost reduction vs text-embedding-3-small on high-volume indexing
  - Consistent vectors (no API versioning drift)

BGE-small-en-v1.5 is 33M parameters, fast on CPU, good quality for clinical text.
For higher quality at the cost of speed, swap for BAAI/bge-large-en-v1.5.
"""

import logging
from dataclasses import dataclass

import numpy as np
from sentence_transformers import SentenceTransformer

from src.config import Settings

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingModel:
    model: SentenceTransformer
    model_id: str
    dimension: int


def load_embedding_model(settings: Settings, device: str) -> EmbeddingModel:
    """Load BGE embedding model. Called once by the registry."""
    model = SentenceTransformer(
        settings.embedding_model_id,
        device=device,
        cache_folder=settings.model_cache_dir,
    )
    # Detect embedding dimension from a dummy encode
    sample = model.encode(["test"], convert_to_numpy=True)
    dimension = sample.shape[1]
    logger.info(f"Embedding model loaded. Dimension: {dimension}")

    return EmbeddingModel(model=model, model_id=settings.embedding_model_id, dimension=dimension)


def embed_texts(
    model: EmbeddingModel,
    texts: list[str],
    normalize: bool = True,
    batch_size: int = 32,
) -> list[list[float]]:
    """
    Generate embeddings for a list of texts.

    Args:
        model: Loaded EmbeddingModel from registry
        texts: Input strings to embed
        normalize: L2-normalize vectors (recommended for cosine similarity)
        batch_size: Number of texts to encode per batch

    Returns:
        List of embedding vectors, one per input text.
        Each vector is a list of floats (dimension = 384 for bge-small).
    """
    if not texts:
        return []

    # Filter out empty strings
    non_empty = [(i, t) for i, t in enumerate(texts) if t and t.strip()]
    if not non_empty:
        return [[] for _ in texts]

    indices, clean_texts = zip(*non_empty)

    # BGE-small: prepend "Represent this sentence: " for better retrieval quality
    # (official BGE instruction for retrieval tasks)
    prefixed = [f"Represent this sentence: {t}" for t in clean_texts]

    vectors = model.model.encode(
        prefixed,
        batch_size=batch_size,
        normalize_embeddings=normalize,
        convert_to_numpy=True,
        show_progress_bar=False,
    )

    # Reconstruct full list (maintain original indices, use zero vector for empty)
    result: list[list[float]] = [[] for _ in texts]
    for original_idx, vector in zip(indices, vectors):
        result[original_idx] = vector.tolist()

    return result


def embed_query(model: EmbeddingModel, query: str, normalize: bool = True) -> list[float]:
    """
    Embed a single query string.
    Slightly different prefix from document embedding (standard BGE practice).
    """
    if not query or not query.strip():
        raise ValueError("Query must not be empty")

    # BGE query prefix
    prefixed = f"Represent this query for searching relevant passages: {query}"
    vector = model.model.encode(
        [prefixed],
        normalize_embeddings=normalize,
        convert_to_numpy=True,
        show_progress_bar=False,
    )[0]
    return vector.tolist()

"""
Cross-encoder reranker for RAG retrieval quality.

Model: cross-encoder/ms-marco-MiniLM-L-6-v2
Task: Sentence Pair Scoring (Retrieval Reranking)
Use in ClinicalMind: Rerank top-20 RAG candidates → top-5 for LLM context.

The cross-encoder scores each (query, passage) pair jointly — more accurate
than dot-product similarity but O(n) vs O(1) per query, so run on a small
candidate set after initial vector retrieval (typically top 20).
"""

import logging
from dataclasses import dataclass

from sentence_transformers import CrossEncoder

from src.config import Settings

logger = logging.getLogger(__name__)


@dataclass
class RerankerModel:
    model: CrossEncoder
    model_id: str


@dataclass
class RankedPassage:
    passage: str
    score: float        # raw cross-encoder score (higher = more relevant)
    rank: int           # 1-based rank after reranking
    original_index: int # index in the original candidate list


def load_reranker_model(settings: Settings, device: str) -> RerankerModel:
    """Load cross-encoder reranker. Called once by the registry."""
    model = CrossEncoder(
        settings.reranker_model_id,
        device=device,
        cache_folder=settings.model_cache_dir,
    )
    return RerankerModel(model=model, model_id=settings.reranker_model_id)


def run_rerank(
    model: RerankerModel,
    query: str,
    passages: list[str],
    top_k: int = 5,
) -> list[RankedPassage]:
    """
    Rerank a list of candidate passages for a given query.

    Args:
        model: Loaded RerankerModel from registry
        query: The user's clinical question
        passages: Candidate passages from initial vector retrieval (typically 20)
        top_k: Number of top-ranked passages to return

    Returns:
        Top-k passages sorted by cross-encoder score descending.
        Includes original index so the caller can map back to chunk IDs.
    """
    if not passages:
        return []
    if not query or not query.strip():
        raise ValueError("Query must not be empty")

    top_k = min(top_k, len(passages))

    pairs = [(query, p) for p in passages]
    scores = model.model.predict(
        pairs,
        batch_size=min(len(pairs), 16),
        show_progress_bar=False,
    )

    # Sort by score descending, take top_k
    ranked = sorted(
        enumerate(zip(passages, scores)),
        key=lambda x: x[1][1],
        reverse=True,
    )[:top_k]

    return [
        RankedPassage(
            passage=passage,
            score=round(float(score), 4),
            rank=rank + 1,
            original_index=original_idx,
        )
        for rank, (original_idx, (passage, score)) in enumerate(ranked)
    ]

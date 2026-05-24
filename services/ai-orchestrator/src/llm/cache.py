"""
Semantic Cache — Redis-backed similarity cache for LLM responses.

Avoids repeat LLM calls for semantically similar queries.
Uses embedding cosine similarity to detect near-duplicate questions.
Expected cache hit rate: ~34% in a busy ward environment.
"""

import hashlib
import json
import logging
from typing import Optional

import numpy as np

from src.config import Settings

logger = logging.getLogger(__name__)


class SemanticCache:
    """
    Two-level cache:
    Level 1: Exact hash match (free, instant)
    Level 2: Embedding similarity match (requires embedding call)
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self._redis = None

    def _get_redis(self):
        if self._redis is None:
            import redis
            self._redis = redis.from_url(
                self.settings.redis_url,
                decode_responses=True,
            )
        return self._redis

    def _exact_key(self, query: str, patient_id: str) -> str:
        """Exact match key: hash of (normalised_query, patient_id)."""
        normalised = " ".join(query.lower().split())
        payload = f"{patient_id}:{normalised}"
        return f"cache:exact:{hashlib.sha256(payload.encode()).hexdigest()}"

    def get_exact(self, query: str, patient_id: str) -> Optional[str]:
        """Check exact cache. Returns cached answer string or None."""
        try:
            r = self._get_redis()
            return r.get(self._exact_key(query, patient_id))
        except Exception as e:
            logger.debug(f"Cache get failed: {e}")
            return None

    def set_exact(self, query: str, patient_id: str, answer: str) -> None:
        """Store an answer in the exact cache."""
        try:
            r = self._get_redis()
            r.setex(
                self._exact_key(query, patient_id),
                self.settings.semantic_cache_ttl_seconds,
                answer,
            )
        except Exception as e:
            logger.debug(f"Cache set failed: {e}")

    def get_semantic(
        self,
        query_embedding: list[float],
        patient_id: str,
        top_k: int = 5,
    ) -> Optional[str]:
        """
        Check semantic cache using embedding similarity.
        Scans recent cache entries for the patient and returns
        the best match above the similarity threshold.
        """
        try:
            r = self._get_redis()
            pattern = f"cache:semantic:{patient_id}:*"
            keys = list(r.scan_iter(pattern, count=100))[:50]

            if not keys:
                return None

            query_vec = np.array(query_embedding)
            best_score = 0.0
            best_answer = None

            for key in keys:
                raw = r.get(key)
                if not raw:
                    continue
                entry = json.loads(raw)
                cached_vec = np.array(entry["embedding"])
                # Cosine similarity
                score = float(np.dot(query_vec, cached_vec) / (
                    np.linalg.norm(query_vec) * np.linalg.norm(cached_vec) + 1e-8
                ))
                if score > best_score:
                    best_score = score
                    best_answer = entry["answer"]

            threshold = self.settings.semantic_cache_similarity_threshold
            if best_score >= threshold and best_answer:
                logger.info(f"Semantic cache HIT (score={best_score:.3f})")
                return best_answer

            return None
        except Exception as e:
            logger.debug(f"Semantic cache lookup failed: {e}")
            return None

    def set_semantic(
        self,
        query: str,
        patient_id: str,
        embedding: list[float],
        answer: str,
    ) -> None:
        """Store an answer in the semantic cache with its embedding."""
        try:
            import uuid
            r = self._get_redis()
            key = f"cache:semantic:{patient_id}:{uuid.uuid4().hex}"
            r.setex(
                key,
                self.settings.semantic_cache_ttl_seconds,
                json.dumps({"query": query, "embedding": embedding, "answer": answer}),
            )
        except Exception as e:
            logger.debug(f"Semantic cache write failed: {e}")

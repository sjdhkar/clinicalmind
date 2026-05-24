"""
EvidenceRetrievalAgent — hybrid RAG pipeline.

Stage 1: Metadata pre-filter (patient_id + time window)
Stage 2: Hybrid dense (pgvector) + sparse (BM25) retrieval, merged with RRF
Stage 3: Cross-encoder reranking via HF sidecar
"""

import logging
import httpx

from src.config import Settings
from src.models.clinical_state import ClinicalState, RetrievedChunk

logger = logging.getLogger(__name__)


async def _embed_query(query: str, settings: Settings) -> list[float]:
    """Get query embedding from HF sidecar (local BGE model)."""
    async with httpx.AsyncClient(timeout=settings.hf_inference_timeout_seconds) as client:
        resp = await client.post(
            f"{settings.hf_inference_url}/embed/query",
            json={"query": query},
        )
        resp.raise_for_status()
        return resp.json()["embedding"]


async def _rerank_passages(
    query: str,
    passages: list[str],
    settings: Settings,
) -> list[dict]:
    """Rerank candidate passages using cross-encoder via HF sidecar."""
    async with httpx.AsyncClient(timeout=settings.hf_inference_timeout_seconds) as client:
        resp = await client.post(
            f"{settings.hf_inference_url}/rerank",
            json={"query": query, "passages": passages, "top_k": settings.rag_top_k_rerank},
        )
        resp.raise_for_status()
        return resp.json()["results"]


def node_evidence_retrieval(state: ClinicalState, settings: Settings) -> dict:
    """
    LangGraph node: hybrid RAG retrieval for the patient query.

    Returns top-K chunks after dense + sparse retrieval and cross-encoder reranking.
    """
    import asyncio

    loop = asyncio.new_event_loop()
    try:
        chunks = loop.run_until_complete(
            _retrieve(state, settings)
        )
    except Exception as e:
        logger.error(f"[{state['trace_id']}] Evidence retrieval failed: {e}")
        chunks = []
    finally:
        loop.close()

    logger.info(
        f"[{state['trace_id']}] Retrieved {len(chunks)} chunks "
        f"for patient={state['patient_id']}"
    )
    return {"retrieved_chunks": chunks}


async def _retrieve(state: ClinicalState, settings: Settings) -> list[RetrievedChunk]:
    """Full hybrid retrieval pipeline."""
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import text

    # Step 1: Get query embedding from HF sidecar
    query_embedding = await _embed_query(state["query"], settings)
    embedding_str = f"[{','.join(str(v) for v in query_embedding)}]"

    engine = create_async_engine(settings.database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Step 2: Dense retrieval (pgvector cosine similarity)
        # Filtered by patient_id and encounter_id before ANN search
        dense_sql = text("""
            SELECT
                id::text as chunk_id,
                content,
                source_type,
                archetype_id,
                timestamp::text as timestamp,
                1 - (embedding <=> :embedding::vector) as similarity_score
            FROM clinical_chunks
            WHERE
                patient_id = :patient_id
                AND encounter_id = :encounter_id
                AND created_at > NOW() - INTERVAL ':ttl hours'
            ORDER BY embedding <=> :embedding::vector
            LIMIT :top_k
        """)

        dense_rows = await session.execute(dense_sql, {
            "embedding": embedding_str,
            "patient_id": state["patient_id"],
            "encounter_id": state["encounter_id"],
            "ttl": settings.rag_chunk_ttl_hours,
            "top_k": settings.rag_top_k_retrieval,
        })
        dense_results = dense_rows.mappings().all()

        # Step 3: BM25 sparse retrieval via pg_bm25 (ParadeDB)
        # Falls back gracefully if pg_bm25 not installed
        sparse_results = []
        try:
            sparse_sql = text("""
                SELECT
                    id::text as chunk_id,
                    content,
                    source_type,
                    archetype_id,
                    timestamp::text as timestamp,
                    paradedb.score(id) as similarity_score
                FROM clinical_chunks
                WHERE
                    patient_id = :patient_id
                    AND encounter_id = :encounter_id
                    AND content @@@ :query
                LIMIT :top_k
            """)
            sparse_rows = await session.execute(sparse_sql, {
                "patient_id": state["patient_id"],
                "encounter_id": state["encounter_id"],
                "query": state["query"],
                "top_k": settings.rag_top_k_retrieval // 2,
            })
            sparse_results = sparse_rows.mappings().all()
        except Exception:
            logger.debug("BM25 retrieval unavailable (pg_bm25 not installed)")

    await engine.dispose()

    # Step 4: Reciprocal Rank Fusion merge
    all_candidates = _rrf_merge(dense_results, sparse_results)

    if not all_candidates:
        return []

    # Step 5: Cross-encoder reranking
    passages = [r["content"] for r in all_candidates]
    try:
        reranked = await _rerank_passages(state["query"], passages, settings)
        final_chunks = [
            RetrievedChunk(
                chunk_id=all_candidates[r["original_index"]]["chunk_id"],
                content=r["passage"],
                source_type=all_candidates[r["original_index"]].get("source_type", "unknown"),
                archetype_id=all_candidates[r["original_index"]].get("archetype_id"),
                timestamp=all_candidates[r["original_index"]].get("timestamp"),
                similarity_score=all_candidates[r["original_index"]].get("similarity_score", 0.0),
                rerank_score=r["score"],
            )
            for r in reranked
        ]
    except Exception as e:
        logger.warning(f"Reranking failed, using dense order: {e}")
        final_chunks = [
            RetrievedChunk(
                chunk_id=row["chunk_id"],
                content=row["content"],
                source_type=row.get("source_type", "unknown"),
                archetype_id=row.get("archetype_id"),
                timestamp=row.get("timestamp"),
                similarity_score=float(row.get("similarity_score", 0.0)),
            )
            for row in all_candidates[:settings.rag_top_k_rerank]
        ]

    return final_chunks


def _rrf_merge(
    dense: list,
    sparse: list,
    k: int = 60,
) -> list[dict]:
    """
    Reciprocal Rank Fusion — merge dense and sparse results.

    RRF score = 1/(k + rank_dense) + 1/(k + rank_sparse)
    where k=60 is the standard smoothing constant.
    """
    scores: dict[str, float] = {}
    meta: dict[str, dict] = {}

    for rank, row in enumerate(dense):
        cid = row["chunk_id"]
        scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank + 1)
        meta[cid] = dict(row)

    for rank, row in enumerate(sparse):
        cid = row["chunk_id"]
        scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank + 1)
        if cid not in meta:
            meta[cid] = dict(row)

    sorted_ids = sorted(scores.keys(), key=lambda cid: scores[cid], reverse=True)
    return [meta[cid] for cid in sorted_ids]

"""
Ingest endpoint — document ingestion pipeline for RAG corpus.

Accepts clinical documents (observation archetypes, nursing notes, protocol PDFs)
chunks them with domain-aware chunkers, embeds via HF sidecar, and stores in pgvector.
"""

import logging
import uuid
from enum import Enum

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field

from src.config import Settings, get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ingest", tags=["ingest"])


class DocumentType(str, Enum):
    OBSERVATION = "observation"       # OpenEHR archetype JSON
    NURSING_NOTE = "nursing_note"     # Free text
    PROTOCOL_PDF = "protocol_pdf"     # Clinical guidelines


class IngestRequest(BaseModel):
    patient_id: str
    encounter_id: str
    document_type: DocumentType
    content: str = Field(..., min_length=1, max_length=100_000)
    metadata: dict = Field(default_factory=dict)


class IngestResponse(BaseModel):
    job_id: str
    status: str
    document_type: str
    message: str


async def _ingest_document(
    job_id: str,
    request: IngestRequest,
    settings: Settings,
) -> None:
    """
    Background ingestion pipeline:
    1. Chunk with domain-aware chunker (archetype / sentence / hierarchical)
    2. Get embeddings from HF sidecar (/embed/texts)
    3. Store chunks + vectors in pgvector with metadata
    """
    import httpx
    from src.rag.chunkers import chunk_document

    logger.info(f"[{job_id}] Starting ingestion: type={request.document_type}")

    try:
        # Step 1: Chunk
        chunks = chunk_document(
            content=request.content,
            document_type=request.document_type.value,
            metadata={
                "patient_id": request.patient_id,
                "encounter_id": request.encounter_id,
                **request.metadata,
            },
        )
        logger.info(f"[{job_id}] Created {len(chunks)} chunks")

        # Step 2: Embed
        async with httpx.AsyncClient(timeout=30) as client:
            embed_resp = await client.post(
                f"{settings.hf_inference_url}/embed/texts",
                json={"texts": [c["content"] for c in chunks]},
            )
            embed_resp.raise_for_status()
            embeddings = embed_resp.json()["embeddings"]

        # Step 3: Store in pgvector
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy import text

        engine = create_async_engine(settings.database_url)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with async_session() as session:
            for chunk, embedding in zip(chunks, embeddings):
                await session.execute(
                    text("""
                        INSERT INTO clinical_chunks
                            (id, patient_id, encounter_id, content, source_type,
                             archetype_id, timestamp, embedding, metadata)
                        VALUES
                            (:id, :patient_id, :encounter_id, :content, :source_type,
                             :archetype_id, :timestamp, :embedding::vector, :metadata::jsonb)
                        ON CONFLICT (id) DO NOTHING
                    """),
                    {
                        "id": str(uuid.uuid4()),
                        "patient_id": request.patient_id,
                        "encounter_id": request.encounter_id,
                        "content": chunk["content"],
                        "source_type": chunk["source_type"],
                        "archetype_id": chunk.get("archetype_id"),
                        "timestamp": chunk.get("timestamp"),
                        "embedding": f"[{','.join(str(v) for v in embedding)}]",
                        "metadata": str(chunk.get("metadata", {})),
                    },
                )
            await session.commit()

        await engine.dispose()
        logger.info(f"[{job_id}] Ingestion complete: {len(chunks)} chunks stored")

    except Exception as e:
        logger.error(f"[{job_id}] Ingestion failed: {e}")


@router.post("", response_model=IngestResponse, summary="Ingest clinical document")
async def ingest_document(
    request: IngestRequest,
    background_tasks: BackgroundTasks,
    settings: Settings = Depends(get_settings),
) -> IngestResponse:
    """
    Ingest a clinical document into the RAG corpus.
    Processing is async (returns immediately with job_id).
    """
    job_id = str(uuid.uuid4())
    background_tasks.add_task(_ingest_document, job_id, request, settings)

    return IngestResponse(
        job_id=job_id,
        status="queued",
        document_type=request.document_type.value,
        message=f"Document queued for ingestion. job_id={job_id}",
    )

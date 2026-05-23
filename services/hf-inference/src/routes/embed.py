"""Embeddings endpoint — local vector generation for RAG pipeline."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.config import Settings, get_settings
from src.models.embeddings import embed_query, embed_texts, load_embedding_model
from src.models.registry import get_model

router = APIRouter(prefix="/embed", tags=["embeddings"])


class EmbedTextsRequest(BaseModel):
    texts: list[str] = Field(
        ...,
        min_length=1,
        max_length=200,
        description="List of texts to embed (chunks for indexing)",
    )
    normalize: bool = Field(
        default=True,
        description="L2-normalize vectors (recommended for cosine similarity with pgvector)",
    )


class EmbedQueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1024)
    normalize: bool = Field(default=True)


class EmbedTextsResponse(BaseModel):
    embeddings: list[list[float]]
    dimension: int
    count: int
    model_id: str


class EmbedQueryResponse(BaseModel):
    embedding: list[float]
    dimension: int
    model_id: str


@router.post("/texts", response_model=EmbedTextsResponse, summary="Embed documents/chunks")
async def embed_document_texts(
    request: EmbedTextsRequest,
    settings: Settings = Depends(get_settings),
) -> EmbedTextsResponse:
    """
    Generate embeddings for a list of text chunks (for indexing into pgvector).

    Uses BGE document prefix for better retrieval quality.
    Batches automatically — safe to send up to 200 texts per call.
    """
    try:
        model = get_model("embeddings", load_embedding_model, settings)
        vectors = embed_texts(
            model,
            request.texts,
            normalize=request.normalize,
            batch_size=settings.embedding_batch_size,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Embedding failed: {str(e)}") from e

    return EmbedTextsResponse(
        embeddings=vectors,
        dimension=model.dimension,
        count=len(vectors),
        model_id=model.model_id,
    )


@router.post("/query", response_model=EmbedQueryResponse, summary="Embed a search query")
async def embed_search_query(
    request: EmbedQueryRequest,
    settings: Settings = Depends(get_settings),
) -> EmbedQueryResponse:
    """
    Generate an embedding for a single search query (for retrieval).

    Uses BGE query prefix (different from document prefix — important for quality).
    """
    try:
        model = get_model("embeddings", load_embedding_model, settings)
        vector = embed_query(model, request.query, normalize=request.normalize)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query embedding failed: {str(e)}") from e

    return EmbedQueryResponse(
        embedding=vector,
        dimension=model.dimension,
        model_id=model.model_id,
    )

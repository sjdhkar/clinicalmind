"""Reranking endpoint — cross-encoder reranking for RAG quality."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.config import Settings, get_settings
from src.models.registry import get_model
from src.models.reranker import load_reranker_model, run_rerank

router = APIRouter(prefix="/rerank", tags=["rerank"])


class RerankRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1024)
    passages: list[str] = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Candidate passages from initial vector retrieval (typically top 20)",
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of top passages to return after reranking",
    )


class RankedPassageResponse(BaseModel):
    passage: str
    score: float
    rank: int
    original_index: int


class RerankResponse(BaseModel):
    results: list[RankedPassageResponse]
    model_id: str


@router.post("", response_model=RerankResponse, summary="Cross-encoder reranking")
async def rerank_passages(
    request: RerankRequest,
    settings: Settings = Depends(get_settings),
) -> RerankResponse:
    """
    Rerank candidate passages using a cross-encoder model.

    More accurate than vector similarity for determining which retrieved chunk
    is most relevant to the query. Run this after initial ANN retrieval to
    reduce the context window from top-20 to top-5.
    """
    try:
        model = get_model("reranker", load_reranker_model, settings)
        results = run_rerank(model, request.query, request.passages, request.top_k)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reranking failed: {str(e)}") from e

    return RerankResponse(
        results=[
            RankedPassageResponse(
                passage=r.passage,
                score=r.score,
                rank=r.rank,
                original_index=r.original_index,
            )
            for r in results
        ],
        model_id=model.model_id,
    )

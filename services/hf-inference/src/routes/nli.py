"""NLI endpoint — hallucination claim verification."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.config import Settings, get_settings
from src.models.nli import NliVerdict, load_nli_model, verify_claim, verify_claims_batch
from src.models.registry import get_model

router = APIRouter(prefix="/nli", tags=["nli"])


class NliRequest(BaseModel):
    claim: str = Field(
        ...,
        min_length=1,
        max_length=1024,
        description="Factual claim from the LLM response to verify",
        examples=["The patient's SpO2 was recorded as 91% at 14:32."],
    )
    passage: str = Field(
        ...,
        min_length=1,
        max_length=4096,
        description="Retrieved chunk that was cited for this claim (the evidence)",
    )
    pass_threshold: float = Field(default=0.70, ge=0.0, le=1.0)
    warn_threshold: float = Field(default=0.40, ge=0.0, le=1.0)


class NliBatchItem(BaseModel):
    claim: str
    passage: str


class NliBatchRequest(BaseModel):
    items: list[NliBatchItem] = Field(..., min_length=1, max_length=50)
    pass_threshold: float = Field(default=0.70, ge=0.0, le=1.0)
    warn_threshold: float = Field(default=0.40, ge=0.0, le=1.0)


class NliResultResponse(BaseModel):
    entailment_score: float
    neutral_score: float
    contradiction_score: float
    verdict: NliVerdict
    predicted_label: str


class NliBatchResponse(BaseModel):
    results: list[NliResultResponse]
    model_id: str


@router.post("", response_model=NliResultResponse, summary="Single claim verification")
async def verify_single_claim(
    request: NliRequest,
    settings: Settings = Depends(get_settings),
) -> NliResultResponse:
    """
    Verify that a single claim is entailed by its cited passage.

    Verdict meanings:
    - **pass**: entailment_score ≥ pass_threshold — claim is supported
    - **warn**: entailment_score between warn and pass — show with ⚠ in UI
    - **fail**: entailment_score < warn_threshold — block response
    """
    try:
        model = get_model("nli", load_nli_model, settings)
        result = verify_claim(
            model,
            request.claim,
            request.passage,
            request.pass_threshold,
            request.warn_threshold,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"NLI inference failed: {str(e)}") from e

    return NliResultResponse(
        entailment_score=result.entailment_score,
        neutral_score=result.neutral_score,
        contradiction_score=result.contradiction_score,
        verdict=result.verdict,
        predicted_label=result.predicted_label,
    )


@router.post("/batch", response_model=NliBatchResponse, summary="Batch claim verification")
async def verify_batch_claims(
    request: NliBatchRequest,
    settings: Settings = Depends(get_settings),
) -> NliBatchResponse:
    """
    Verify multiple (claim, passage) pairs in a single batch inference call.
    More efficient than sequential single calls when a response has several claims.
    """
    try:
        model = get_model("nli", load_nli_model, settings)
        pairs = [(item.claim, item.passage) for item in request.items]
        results = verify_claims_batch(
            model,
            pairs,
            request.pass_threshold,
            request.warn_threshold,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch NLI failed: {str(e)}") from e

    return NliBatchResponse(
        results=[
            NliResultResponse(
                entailment_score=r.entailment_score,
                neutral_score=r.neutral_score,
                contradiction_score=r.contradiction_score,
                verdict=r.verdict,
                predicted_label=r.predicted_label,
            )
            for r in results
        ],
        model_id=model.model_id,
    )

"""NER endpoint — clinical entity extraction from free text."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.config import Settings, get_settings
from src.models.ner import NerEntity, load_ner_model, run_ner
from src.models.registry import get_model

router = APIRouter(prefix="/ner", tags=["ner"])


class NerRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=1,
        max_length=4096,
        description="Clinical text to extract entities from (nursing note, discharge summary, etc.)",
        examples=["Patient was given metformin 500mg for type 2 diabetes. SpO2 dropped to 91%."],
    )
    min_score: float = Field(
        default=0.75,
        ge=0.0,
        le=1.0,
        description="Minimum confidence score for returned entities",
    )


class NerEntityResponse(BaseModel):
    text: str
    label: str
    score: float
    start: int
    end: int


class NerResponse(BaseModel):
    entities: list[NerEntityResponse]
    entity_count: int
    model_id: str


@router.post("", response_model=NerResponse, summary="Clinical NER")
async def extract_entities(
    request: NerRequest,
    settings: Settings = Depends(get_settings),
) -> NerResponse:
    """
    Extract clinical named entities from free text.

    Returns entities of types: Disease, Chemical, Gene, Protein, Species,
    Cell_Type, Cell_Line, Dna, Rna.

    **Common clinical use:**
    - Drug/medication extraction from nursing notes
    - Diagnosis extraction for RAG chunk metadata enrichment
    - Symptom extraction for deterioration assessment
    """
    try:
        model = get_model("ner", load_ner_model, settings)
        entities: list[NerEntity] = run_ner(model, request.text, request.min_score)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"NER inference failed: {str(e)}") from e

    return NerResponse(
        entities=[
            NerEntityResponse(
                text=e.text,
                label=e.label,
                score=e.score,
                start=e.start,
                end=e.end,
            )
            for e in entities
        ],
        entity_count=len(entities),
        model_id=model.model_id,
    )

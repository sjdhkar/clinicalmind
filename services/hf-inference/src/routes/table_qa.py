"""Table QA endpoint — query lab result tables with natural language."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.config import Settings, get_settings
from src.models.registry import get_model
from src.models.table_qa import load_table_qa_model, run_table_qa

router = APIRouter(prefix="/table-qa", tags=["table-qa"])


class TableQaRequest(BaseModel):
    table: dict[str, list] = Field(
        ...,
        description=(
            "Table as a dict mapping column names to lists of values. "
            "All lists must be the same length. Values will be coerced to strings."
        ),
        examples=[{
            "Date": ["2025-05-18", "2025-05-19", "2025-05-20"],
            "Creatinine (umol/L)": ["88", "102", "118"],
            "eGFR": ["72", "63", "55"],
        }],
    )
    question: str = Field(
        ...,
        min_length=3,
        max_length=512,
        description="Natural language question about the table",
        examples=["What is the trend in creatinine values?"],
    )


class TableQaResponse(BaseModel):
    answer: str
    cells: list[str]
    aggregation: str
    model_id: str


@router.post("", response_model=TableQaResponse, summary="Lab table question answering")
async def answer_table_question(
    request: TableQaRequest,
    settings: Settings = Depends(get_settings),
) -> TableQaResponse:
    """
    Answer a natural language question about a table of lab results or vitals.

    TAPAS supports aggregations: SUM, AVERAGE, COUNT, NONE.
    Works best for factual questions like min/max/trend/count queries.
    """
    try:
        model = get_model("table_qa", load_table_qa_model, settings)
        result = run_table_qa(model, request.table, request.question)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Table QA failed: {str(e)}") from e

    return TableQaResponse(
        answer=result.answer,
        cells=result.cells,
        aggregation=result.aggregation,
        model_id=model.model_id,
    )

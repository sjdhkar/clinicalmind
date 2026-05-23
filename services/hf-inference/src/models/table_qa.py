"""
Table Question Answering using TAPAS.

Model: google/tapas-base-finetuned-wtq
Task: Table Question Answering
Use in ClinicalMind: Query lab result tables without LLM cost.
  e.g. "What was the highest creatinine value in the last 5 days?"
       "What is the trend in WBC count?"
"""

import logging
from dataclasses import dataclass

import pandas as pd
from transformers import TapasForQuestionAnswering, TapasTokenizer, pipeline

from src.config import Settings

logger = logging.getLogger(__name__)


@dataclass
class TableQaModel:
    pipe: object
    model_id: str


@dataclass
class TableQaResult:
    answer: str
    coordinates: list[list[int]]   # row/col coordinates of answer cells
    cells: list[str]               # raw cell values that make up the answer
    aggregation: str               # SUM / AVERAGE / COUNT / NONE


def load_table_qa_model(settings: Settings, device: str) -> TableQaModel:
    """Load TAPAS pipeline. Called once by the registry."""
    device_id = -1 if device == "cpu" else 0

    pipe = pipeline(
        task="table-question-answering",
        model=settings.table_qa_model_id,
        tokenizer=settings.table_qa_model_id,
        device=device_id,
        model_kwargs={"cache_dir": settings.model_cache_dir},
    )
    return TableQaModel(pipe=pipe, model_id=settings.table_qa_model_id)


def run_table_qa(
    model: TableQaModel,
    table: dict[str, list],
    question: str,
) -> TableQaResult:
    """
    Answer a natural language question about a table of clinical data.

    Args:
        model: Loaded TableQaModel from registry
        table: Dict mapping column names to lists of values.
               All lists must be the same length.
               Example: {"Date": ["2025-05-20", ...], "Creatinine": ["1.2", ...]}
               TAPAS requires ALL values to be strings.
        question: Natural language question about the table

    Returns:
        TableQaResult with the answer and supporting cell references

    Note:
        TAPAS works best on tables with < 100 rows and clear column names.
        For very large lab history tables, pre-filter to a relevant date range first.
    """
    if not table:
        raise ValueError("Table must not be empty")
    if not question or not question.strip():
        raise ValueError("Question must not be empty")

    # Ensure all values are strings (TAPAS requirement)
    str_table = {col: [str(v) for v in vals] for col, vals in table.items()}

    # Validate all columns have same length
    lengths = [len(v) for v in str_table.values()]
    if len(set(lengths)) > 1:
        raise ValueError(f"All table columns must have equal length. Got: {lengths}")

    df = pd.DataFrame(str_table)
    raw = model.pipe(table=df, query=question)

    return TableQaResult(
        answer=raw.get("answer", ""),
        coordinates=raw.get("coordinates", []),
        cells=raw.get("cells", []),
        aggregation=raw.get("aggregator", "NONE"),
    )

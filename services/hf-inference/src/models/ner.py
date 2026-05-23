"""
Clinical Named Entity Recognition using Bio_ClinicalBERT.

Model: d4data/biomedical-ner-all
Task: Token Classification
Use in ClinicalMind: Extract drugs, diagnoses, symptoms, procedures from nursing notes.

Output entity types from this model:
  B-DISEASE, I-DISEASE, B-CHEMICAL, I-CHEMICAL, B-GENE, I-GENE,
  B-SPECIES, I-SPECIES, B-CELL_TYPE, I-CELL_TYPE, B-CELL_LINE, I-CELL_LINE,
  B-DNA, I-DNA, B-RNA, I-RNA, B-PROTEIN, I-PROTEIN
"""

import logging
from dataclasses import dataclass

from transformers import AutoModelForTokenClassification, AutoTokenizer, pipeline

from src.config import Settings

logger = logging.getLogger(__name__)


@dataclass
class NerEntity:
    text: str
    label: str          # e.g. "DISEASE", "CHEMICAL"
    score: float        # confidence 0.0–1.0
    start: int          # character offset in original text
    end: int


@dataclass
class NerModel:
    pipe: object  # transformers.Pipeline
    model_id: str


def load_ner_model(settings: Settings, device: str) -> NerModel:
    """Load the NER pipeline. Called once by the registry."""
    # Map torch device string to transformers device int (-1 = CPU, 0 = first GPU)
    device_id = -1 if device == "cpu" else 0

    pipe = pipeline(
        task="ner",
        model=settings.ner_model_id,
        tokenizer=settings.ner_model_id,
        aggregation_strategy="simple",  # merge B-/I- tokens into single spans
        device=device_id,
        model_kwargs={"cache_dir": settings.model_cache_dir},
    )
    return NerModel(pipe=pipe, model_id=settings.ner_model_id)


def run_ner(model: NerModel, text: str, min_score: float = 0.75) -> list[NerEntity]:
    """
    Run NER on a clinical text string.

    Args:
        model: Loaded NerModel from registry
        text: Raw clinical text (nursing note, discharge summary, etc.)
        min_score: Minimum confidence threshold — discard lower-confidence entities

    Returns:
        List of NerEntity, sorted by start offset
    """
    if not text or not text.strip():
        return []

    raw = model.pipe(text)

    entities = []
    for item in raw:
        score = float(item["score"])
        if score < min_score:
            continue

        # Normalise label: strip B-/I- prefix, title-case
        label = item["entity_group"].replace("B-", "").replace("I-", "").title()

        entities.append(
            NerEntity(
                text=item["word"].strip(),
                label=label,
                score=round(score, 4),
                start=item["start"],
                end=item["end"],
            )
        )

    return sorted(entities, key=lambda e: e.start)

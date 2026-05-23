"""
Unit tests for the NER model handler.
Models are mocked — these tests run without downloading any HuggingFace models.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.models.ner import NerEntity, NerModel, run_ner


def make_mock_ner_model(raw_output: list[dict]) -> NerModel:
    """Create a NerModel with a mocked pipeline."""
    mock_pipe = MagicMock(return_value=raw_output)
    return NerModel(pipe=mock_pipe, model_id="mock-ner-model")


class TestRunNer:
    def test_extracts_disease_entity(self):
        raw = [{"entity_group": "DISEASE", "word": "diabetes", "score": 0.95, "start": 20, "end": 28}]
        model = make_mock_ner_model(raw)
        result = run_ner(model, "Patient was diagnosed with diabetes")
        assert len(result) == 1
        assert result[0].label == "Disease"
        assert result[0].text == "diabetes"
        assert result[0].score == 0.95

    def test_extracts_chemical_entity(self):
        raw = [{"entity_group": "CHEMICAL", "word": "metformin", "score": 0.88, "start": 10, "end": 19}]
        model = make_mock_ner_model(raw)
        result = run_ner(model, "Prescribed metformin 500mg")
        assert result[0].label == "Chemical"

    def test_filters_low_confidence_entities(self):
        raw = [
            {"entity_group": "DISEASE", "word": "hypertension", "score": 0.91, "start": 0, "end": 12},
            {"entity_group": "DISEASE", "word": "headache", "score": 0.55, "start": 20, "end": 28},
        ]
        model = make_mock_ner_model(raw)
        result = run_ner(model, "hypertension and headache", min_score=0.75)
        assert len(result) == 1
        assert result[0].text == "hypertension"

    def test_sorts_by_start_offset(self):
        raw = [
            {"entity_group": "CHEMICAL", "word": "aspirin", "score": 0.90, "start": 30, "end": 37},
            {"entity_group": "DISEASE", "word": "pain", "score": 0.85, "start": 10, "end": 14},
        ]
        model = make_mock_ner_model(raw)
        result = run_ner(model, "Patient has pain and was given aspirin")
        assert result[0].start < result[1].start

    def test_empty_text_returns_empty_list(self):
        model = make_mock_ner_model([])
        result = run_ner(model, "")
        assert result == []

    def test_whitespace_only_returns_empty_list(self):
        model = make_mock_ner_model([])
        result = run_ner(model, "   ")
        assert result == []

    def test_normalises_bi_prefix(self):
        """B-DISEASE and I-DISEASE should both become 'Disease'."""
        raw = [
            {"entity_group": "B-DISEASE", "word": "type 2", "score": 0.92, "start": 0, "end": 6},
            {"entity_group": "I-DISEASE", "word": "diabetes", "score": 0.90, "start": 7, "end": 15},
        ]
        model = make_mock_ner_model(raw)
        result = run_ner(model, "type 2 diabetes")
        for entity in result:
            assert entity.label == "Disease"

    def test_strips_whitespace_from_entity_text(self):
        raw = [{"entity_group": "CHEMICAL", "word": " paracetamol ", "score": 0.88, "start": 0, "end": 13}]
        model = make_mock_ner_model(raw)
        result = run_ner(model, " paracetamol ")
        assert result[0].text == "paracetamol"

    def test_multiple_entities_all_returned(self):
        raw = [
            {"entity_group": "DISEASE", "word": "sepsis", "score": 0.97, "start": 0, "end": 6},
            {"entity_group": "CHEMICAL", "word": "vancomycin", "score": 0.93, "start": 20, "end": 30},
            {"entity_group": "GENE", "word": "IL-6", "score": 0.81, "start": 40, "end": 44},
        ]
        model = make_mock_ner_model(raw)
        result = run_ner(model, "sepsis treated with vancomycin, IL-6 elevated")
        assert len(result) == 3

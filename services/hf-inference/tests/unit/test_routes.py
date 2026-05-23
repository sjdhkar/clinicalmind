"""
Unit tests for NLI, reranker, and the health / NER API routes.
Uses FastAPI TestClient — no real models loaded.
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.models.nli import NliResult, NliVerdict, verify_claim, verify_claims_batch
from src.models.reranker import RankedPassage, RerankerModel, run_rerank


# ─── NLI tests ───────────────────────────────────────────────────

class TestNliVerdicts:
    """Test verdict logic with mocked cross-encoder scores."""

    def _make_mock_nli_model(self, raw_scores):
        """Return a NliModel whose cross-encoder returns fixed scores."""
        from src.models.nli import NliModel
        mock_ce = MagicMock()
        mock_ce.predict.return_value = [raw_scores]
        return NliModel(model=mock_ce, model_id="mock-nli")

    def test_high_entailment_returns_pass(self):
        import numpy as np
        # Raw logits that, after softmax, give ~0.85 entailment
        # Labels order: contradiction, entailment, neutral
        model = self._make_mock_nli_model([0.1, 3.0, 0.1])
        result = verify_claim(model, "SpO2 was 91%", "SpO2 recorded as 91% at 14:32")
        assert result.verdict == NliVerdict.PASS
        assert result.entailment_score > 0.70

    def test_low_entailment_returns_fail(self):
        # Logits giving high contradiction, low entailment
        model = self._make_mock_nli_model([3.0, 0.1, 0.1])
        result = verify_claim(model, "BP was normal", "BP was 180/110 — critically elevated")
        assert result.verdict == NliVerdict.FAIL

    def test_empty_claim_raises(self):
        from src.models.nli import NliModel
        model = NliModel(model=MagicMock(), model_id="mock")
        with pytest.raises(ValueError, match="Claim must not be empty"):
            verify_claim(model, "", "some passage")

    def test_empty_passage_raises(self):
        from src.models.nli import NliModel
        model = NliModel(model=MagicMock(), model_id="mock")
        with pytest.raises(ValueError, match="Passage must not be empty"):
            verify_claim(model, "some claim", "")


# ─── Reranker tests ──────────────────────────────────────────────

class TestReranker:
    def _make_mock_reranker(self, scores: list[float]) -> RerankerModel:
        from sentence_transformers import CrossEncoder
        mock_ce = MagicMock(spec=CrossEncoder)
        mock_ce.predict.return_value = scores
        return RerankerModel(model=mock_ce, model_id="mock-reranker")

    def test_results_sorted_by_score_descending(self):
        passages = ["bad passage", "great passage", "ok passage"]
        scores = [0.1, 0.9, 0.5]
        model = self._make_mock_reranker(scores)
        results = run_rerank(model, "clinical query", passages, top_k=3)
        assert results[0].score > results[1].score > results[2].score

    def test_top_k_limits_results(self):
        passages = ["p1", "p2", "p3", "p4", "p5"]
        scores = [0.5, 0.9, 0.3, 0.7, 0.1]
        model = self._make_mock_reranker(scores)
        results = run_rerank(model, "query", passages, top_k=3)
        assert len(results) == 3

    def test_original_index_preserved(self):
        passages = ["low", "high", "mid"]
        scores = [0.1, 0.9, 0.5]
        model = self._make_mock_reranker(scores)
        results = run_rerank(model, "q", passages, top_k=3)
        # Top result should be index 1 ("high")
        assert results[0].original_index == 1
        assert results[0].passage == "high"

    def test_rank_starts_at_1(self):
        passages = ["a", "b", "c"]
        model = self._make_mock_reranker([0.3, 0.8, 0.5])
        results = run_rerank(model, "q", passages, top_k=3)
        ranks = [r.rank for r in results]
        assert ranks == [1, 2, 3]

    def test_empty_passages_returns_empty(self):
        model = self._make_mock_reranker([])
        results = run_rerank(model, "q", [], top_k=5)
        assert results == []

    def test_empty_query_raises(self):
        model = self._make_mock_reranker([0.5])
        with pytest.raises(ValueError, match="Query must not be empty"):
            run_rerank(model, "", ["passage"])


# ─── API Route tests ─────────────────────────────────────────────

@pytest.fixture
def client():
    from src.main import app
    with TestClient(app) as c:
        yield c


class TestHealthRoute:
    def test_health_returns_200(self, client):
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_returns_ok_status(self, client):
        data = client.get("/health").json()
        assert data["status"] == "ok"

    def test_health_includes_model_status(self, client):
        data = client.get("/health").json()
        assert "models_loaded" in data
        expected_keys = {"ner", "timeseries", "table_qa", "reranker", "nli", "embeddings"}
        assert set(data["models_loaded"].keys()) == expected_keys

    def test_health_includes_uptime(self, client):
        data = client.get("/health").json()
        assert "uptime_seconds" in data
        assert data["uptime_seconds"] >= 0


class TestNerRoute:
    def test_ner_returns_entities(self, client):
        mock_entities = [
            {"entity_group": "DISEASE", "word": "sepsis", "score": 0.96, "start": 0, "end": 6}
        ]
        with patch("src.routes.ner.get_model") as mock_get:
            from src.models.ner import NerModel
            mock_get.return_value = NerModel(
                pipe=MagicMock(return_value=mock_entities),
                model_id="mock-ner",
            )
            response = client.post("/ner", json={"text": "sepsis confirmed"})

        assert response.status_code == 200
        data = response.json()
        assert data["entity_count"] == 1
        assert data["entities"][0]["label"] == "Disease"

    def test_ner_empty_text_returns_400(self, client):
        response = client.post("/ner", json={"text": ""})
        assert response.status_code == 422  # Pydantic min_length validation

    def test_ner_too_long_text_returns_422(self, client):
        response = client.post("/ner", json={"text": "x" * 5000})
        assert response.status_code == 422

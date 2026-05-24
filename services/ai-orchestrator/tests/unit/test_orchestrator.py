"""Unit tests for ai-orchestrator — no LLM, no DB, no HF models required."""

import pytest
from src.agents.supervisor import classify_query, decide_agents
from src.agents.deterioration import calculate_news2
from src.models.clinical_state import QueryType, AgentName, RiskLevel, initial_state
from src.llm.router import ModelRouter
from src.rag.chunkers import (
    ArchetypeChunker, ClinicalSentenceChunker, HierarchicalChunker, chunk_document
)
from src.config import Settings


# ── Query classification ──────────────────────────────────────────

class TestQueryClassifier:
    def test_vitals_query(self):
        assert classify_query("What is the patient's SpO2 trend?") == QueryType.VITALS_ANALYSIS

    def test_deterioration_query(self):
        assert classify_query("What is the NEWS2 risk score?") == QueryType.DETERIORATION_RISK

    def test_evidence_query(self):
        assert classify_query("What does the NICE guideline say about sepsis management?") == QueryType.EVIDENCE_LOOKUP

    def test_note_query(self):
        assert classify_query("Summarise the nursing notes from today") == QueryType.NOTE_SUMMARY

    def test_general_query_fallback(self):
        result = classify_query("Hello there")
        assert result == QueryType.GENERAL

    def test_case_insensitive(self):
        assert classify_query("SPO2 TREND ANALYSIS") == QueryType.VITALS_ANALYSIS


class TestAgentDecision:
    def test_vitals_includes_vitals_agent(self):
        agents = decide_agents(QueryType.VITALS_ANALYSIS)
        assert AgentName.VITALS_ANALYST in agents

    def test_deterioration_includes_all_agents(self):
        agents = decide_agents(QueryType.DETERIORATION_RISK)
        assert AgentName.VITALS_ANALYST in agents
        assert AgentName.NOTE_SUMMARIZER in agents
        assert AgentName.DETERIORATION in agents
        assert AgentName.EVIDENCE_RETRIEVAL in agents

    def test_evidence_only_retrieval(self):
        agents = decide_agents(QueryType.EVIDENCE_LOOKUP)
        assert agents == [AgentName.EVIDENCE_RETRIEVAL]


# ── NEWS2 scoring ─────────────────────────────────────────────────

class TestNews2:
    def test_normal_vitals_low_score(self):
        score = calculate_news2(
            respiratory_rate=16, spo2=98, systolic_bp=120,
            heart_rate=75, consciousness="A", temperature=37.0,
        )
        assert score.total_score == 0
        assert score.risk_level == RiskLevel.LOW

    def test_low_spo2_adds_score(self):
        score = calculate_news2(spo2=91)
        assert score.total_score == 3

    def test_critically_low_bp(self):
        score = calculate_news2(systolic_bp=88)
        assert score.total_score == 3

    def test_altered_consciousness_adds_3(self):
        score = calculate_news2(consciousness="V")
        assert score.total_score == 3

    def test_combined_high_risk(self):
        score = calculate_news2(
            respiratory_rate=25, spo2=91, systolic_bp=88,
            heart_rate=125, consciousness="V", temperature=35.0,
        )
        assert score.total_score >= 15
        assert score.risk_level == RiskLevel.CRITICAL

    def test_none_values_skipped(self):
        score = calculate_news2()  # all None
        assert score.total_score == 0

    def test_medium_risk_threshold(self):
        score = calculate_news2(respiratory_rate=22, heart_rate=111)  # 2+2=4
        assert score.risk_level in {RiskLevel.LOW, RiskLevel.MEDIUM}

    def test_high_hr_adds_score(self):
        score = calculate_news2(heart_rate=135)
        assert score.total_score == 3


# ── Model router ─────────────────────────────────────────────────

class TestModelRouter:
    def _settings(self) -> Settings:
        s = Settings()
        s.router_phi3_max_tokens = 500
        s.router_gpt4o_mini_max_tokens = 2000
        return s

    def test_simple_lookup_low_tokens_gets_phi3(self):
        router = ModelRouter(self._settings())
        model = router.route(300, QueryType.EVIDENCE_LOOKUP)
        assert model == "phi-3-mini"

    def test_medium_tokens_gets_mini(self):
        router = ModelRouter(self._settings())
        model = router.route(800, QueryType.NOTE_SUMMARY)
        assert model == "gpt-4o-mini"

    def test_high_tokens_gets_gpt4o(self):
        router = ModelRouter(self._settings())
        model = router.route(3000, QueryType.GENERAL)
        assert model == "gpt-4o"

    def test_deterioration_always_gpt4o(self):
        router = ModelRouter(self._settings())
        model = router.route(100, QueryType.DETERIORATION_RISK)
        assert model == "gpt-4o"

    def test_cost_estimate_gpt4o(self):
        router = ModelRouter(self._settings())
        cost = router.estimate_cost_usd("gpt-4o", 1000, 200)
        assert cost > 0

    def test_phi3_is_free(self):
        router = ModelRouter(self._settings())
        cost = router.estimate_cost_usd("phi-3-mini", 1000, 200)
        assert cost == 0.0


# ── Chunkers ─────────────────────────────────────────────────────

class TestArchetypeChunker:
    def test_chunks_single_archetype(self):
        import json
        content = json.dumps({
            "archetype_id": "openEHR-EHR-OBSERVATION.blood_pressure.v2",
            "systolic": 120,
            "diastolic": 80,
            "time": "2025-05-22T14:32:00Z",
        })
        chunks = ArchetypeChunker().chunk(content, {"patient_id": "p1"})
        assert len(chunks) == 1
        assert chunks[0]["source_type"] == "observation"
        assert "blood_pressure" in chunks[0]["archetype_id"]

    def test_chunks_array_of_archetypes(self):
        import json
        content = json.dumps([
            {"archetype_id": "obs.bp.v1", "value": 120},
            {"archetype_id": "obs.bp.v1", "value": 118},
        ])
        chunks = ArchetypeChunker().chunk(content, {})
        assert len(chunks) == 2

    def test_invalid_json_falls_back(self):
        chunks = ArchetypeChunker().chunk("not json", {})
        assert len(chunks) == 1
        assert chunks[0]["content"] == "not json"


class TestClinicalSentenceChunker:
    def test_splits_into_multiple_chunks(self):
        note = (
            "Patient was admitted at 08:00. SpO2 was 95%. "
            "Nurse administered oxygen at 2L/min. Patient reported chest pain. "
            "Dr Smith was notified. Blood cultures were taken. "
            "Patient appeared comfortable by 10:00. Temperature was 37.2°C."
        )
        chunks = ClinicalSentenceChunker().chunk(note, {})
        assert len(chunks) >= 1
        for chunk in chunks:
            assert chunk["source_type"] == "nursing_note"

    def test_empty_text_returns_empty(self):
        chunks = ClinicalSentenceChunker().chunk("", {})
        assert chunks == []


class TestHierarchicalChunker:
    def test_splits_by_section(self):
        content = """# Introduction
This is the introduction paragraph.

# Management
Administer fluids immediately.

Give antibiotics within one hour."""
        chunks = HierarchicalChunker().chunk(content, {})
        assert len(chunks) >= 2

    def test_chunk_includes_section_title(self):
        content = "# Sepsis Protocol\nGive fluids immediately."
        chunks = HierarchicalChunker().chunk(content, {})
        if chunks:
            assert "Sepsis Protocol" in chunks[0]["content"]


class TestChunkDocumentRouter:
    def test_routes_observation(self):
        import json
        chunks = chunk_document(
            json.dumps({"archetype_id": "obs.test.v1", "value": 42}),
            "observation",
            {},
        )
        assert chunks[0]["source_type"] == "observation"

    def test_routes_nursing_note(self):
        chunks = chunk_document("Patient was stable. No concerns noted.", "nursing_note", {})
        assert chunks[0]["source_type"] == "nursing_note"

    def test_unknown_type_falls_back_to_sentence(self):
        chunks = chunk_document("Some text here. More text.", "unknown_type", {})
        assert len(chunks) >= 1

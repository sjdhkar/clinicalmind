"""
ClinicalState — the typed shared state for the LangGraph agent graph.

Every agent reads from and writes to this state object.
Using TypedDict enforces a clear contract between agents.
LangGraph serialises this to JSON for checkpointing.

Design principle: state is append-only per field where possible.
Agents add their results; they never delete or overwrite other agents' work.
"""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Any
from typing_extensions import TypedDict

from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field


# ── Enums ────────────────────────────────────────────────────────

class QueryType(str, Enum):
    VITALS_ANALYSIS = "vitals_analysis"
    NOTE_SUMMARY = "note_summary"
    EVIDENCE_LOOKUP = "evidence_lookup"
    DETERIORATION_RISK = "deterioration_risk"
    GENERAL = "general"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AgentName(str, Enum):
    SUPERVISOR = "supervisor"
    VITALS_ANALYST = "vitals_analyst"
    NOTE_SUMMARIZER = "note_summarizer"
    EVIDENCE_RETRIEVAL = "evidence_retrieval"
    DETERIORATION = "deterioration"


# ── Sub-models (written by individual agents) ────────────────────

class RetrievedChunk(BaseModel):
    chunk_id: str
    content: str
    source_type: str          # "observation" | "nursing_note" | "protocol"
    archetype_id: str | None = None
    timestamp: str | None = None
    similarity_score: float
    rerank_score: float | None = None


class NerEntity(BaseModel):
    text: str
    label: str                # Disease | Chemical | Protein etc.
    score: float


class VitalsAnalysis(BaseModel):
    """Output of VitalsAnalystAgent."""
    vital_sign: str
    history: list[float]
    forecast_mean: list[float]
    forecast_low: list[float]
    forecast_high: list[float]
    anomaly_score: float
    anomaly_detected: bool
    narrative: str            # GPT-4o synthesis of the anomaly


class NoteSummary(BaseModel):
    """Output of NoteSummarizerAgent."""
    summary: str
    key_entities: list[NerEntity]
    time_window_hours: int


class News2Score(BaseModel):
    """Calculated NEWS2 early warning score."""
    total_score: int
    risk_level: RiskLevel
    respiratory_rate: int | None = None
    spo2: float | None = None
    systolic_bp: int | None = None
    heart_rate: int | None = None
    consciousness: str | None = None
    temperature: float | None = None


class DeteriorationAssessment(BaseModel):
    """Output of DeteriorationAgent."""
    news2: News2Score
    risk_narrative: str
    recommended_action: str
    confidence: float


class CitedClaim(BaseModel):
    """A single claim in the final response with its NLI verification."""
    claim: str
    chunk_id: str
    entailment_score: float
    verdict: str              # pass | warn | fail


class ClinicalResponse(BaseModel):
    """The final structured response returned to the API layer."""
    answer: str
    citations: list[RetrievedChunk]
    cited_claims: list[CitedClaim]
    agents_used: list[AgentName]
    model_used: str
    prompt_version: str
    trace_id: str
    insufficient_data: bool = False


# ── Main LangGraph State ─────────────────────────────────────────

class ClinicalState(TypedDict):
    # ── Input (set once by the API, never mutated) ────────────
    query: str
    patient_id: str
    encounter_id: str
    user_id: str
    trace_id: str

    # ── Routing (set by supervisor) ───────────────────────────
    query_type: QueryType
    agents_to_run: list[AgentName]
    estimated_tokens: int

    # ── Agent outputs (each agent writes its own field) ───────
    retrieved_chunks: list[RetrievedChunk]
    vitals_analysis: VitalsAnalysis | None
    note_summary: NoteSummary | None
    deterioration_assessment: DeteriorationAssessment | None

    # ── LLM layer ─────────────────────────────────────────────
    model_to_use: str          # gpt-4o | gpt-4o-mini | phi-3-mini
    prompt_version: str
    system_prompt: str
    user_prompt: str           # assembled by supervisor before LLM call

    # ── Final output ──────────────────────────────────────────
    final_response: ClinicalResponse | None
    error: str | None


def initial_state(
    query: str,
    patient_id: str,
    encounter_id: str,
    user_id: str,
    trace_id: str,
) -> ClinicalState:
    """Create a fresh ClinicalState for a new query."""
    return ClinicalState(
        query=query,
        patient_id=patient_id,
        encounter_id=encounter_id,
        user_id=user_id,
        trace_id=trace_id,
        query_type=QueryType.GENERAL,
        agents_to_run=[],
        estimated_tokens=0,
        retrieved_chunks=[],
        vitals_analysis=None,
        note_summary=None,
        deterioration_assessment=None,
        model_to_use="gpt-4o-mini",
        prompt_version="",
        system_prompt="",
        user_prompt="",
        final_response=None,
        error=None,
    )

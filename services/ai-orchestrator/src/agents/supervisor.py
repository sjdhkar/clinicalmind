"""
Supervisor Agent — LangGraph StateGraph orchestrator.

Responsibilities:
  1. Classify the incoming query (QueryType)
  2. Decide which specialist agents to run (and in what order)
  3. Assemble the final prompt from all agent outputs
  4. Run the synthesis LLM call and produce ClinicalResponse
  5. Verify claims via NLI before returning

The graph is: supervisor_route → [agents in parallel] → supervisor_synthesise → END
"""

import logging
import uuid
from typing import Literal

from langgraph.graph import END, START, StateGraph

from src.config import Settings
from src.llm.router import ModelRouter
from src.models.clinical_state import (
    AgentName, CitedClaim, ClinicalResponse, ClinicalState,
    QueryType, RetrievedChunk,
)

logger = logging.getLogger(__name__)


# ── Query intent classifier ───────────────────────────────────────

QUERY_ROUTING_RULES: dict[QueryType, list[str]] = {
    QueryType.VITALS_ANALYSIS: [
        "vital", "spo2", "heart rate", "blood pressure", "temperature",
        "respiratory rate", "oxygen", "pulse", "bp", "hr", "rr", "trend",
        "deteriorat", "forecast", "predict",
    ],
    QueryType.NOTE_SUMMARY: [
        "note", "nursing", "summary", "handover", "assessment", "documented",
        "recorded", "said", "reported", "observed",
    ],
    QueryType.DETERIORATION_RISK: [
        "risk", "news2", "early warning", "score", "deteriorat",
        "concern", "worsen", "escalat",
    ],
    QueryType.EVIDENCE_LOOKUP: [
        "guideline", "protocol", "nice", "evidence", "recommend",
        "treatment", "management", "dose", "when should",
    ],
}


def classify_query(query: str) -> QueryType:
    """Rule-based query classifier. Replace with a fine-tuned classifier in production."""
    q = query.lower()
    scores: dict[QueryType, int] = {qt: 0 for qt in QueryType}
    for query_type, keywords in QUERY_ROUTING_RULES.items():
        scores[query_type] = sum(1 for kw in keywords if kw in q)

    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else QueryType.GENERAL


def decide_agents(query_type: QueryType) -> list[AgentName]:
    """Map query type → list of agents to invoke."""
    routing = {
        QueryType.VITALS_ANALYSIS: [
            AgentName.VITALS_ANALYST,
            AgentName.EVIDENCE_RETRIEVAL,
        ],
        QueryType.NOTE_SUMMARY: [
            AgentName.NOTE_SUMMARIZER,
            AgentName.EVIDENCE_RETRIEVAL,
        ],
        QueryType.DETERIORATION_RISK: [
            AgentName.VITALS_ANALYST,
            AgentName.NOTE_SUMMARIZER,
            AgentName.DETERIORATION,
            AgentName.EVIDENCE_RETRIEVAL,
        ],
        QueryType.EVIDENCE_LOOKUP: [
            AgentName.EVIDENCE_RETRIEVAL,
        ],
        QueryType.GENERAL: [
            AgentName.EVIDENCE_RETRIEVAL,
            AgentName.NOTE_SUMMARIZER,
        ],
    }
    return routing.get(query_type, [AgentName.EVIDENCE_RETRIEVAL])


# ── LangGraph nodes ───────────────────────────────────────────────

def node_supervisor_route(state: ClinicalState) -> dict:
    """
    Node 1: Classify query and decide which agents to run.
    Also estimates token count for model routing.
    """
    query_type = classify_query(state["query"])
    agents = decide_agents(query_type)

    # Rough token estimate: query length + expected context per agent
    estimated = len(state["query"].split()) * 2 + len(agents) * 300

    logger.info(
        f"[{state['trace_id']}] query_type={query_type} agents={[a.value for a in agents]}"
    )
    return {
        "query_type": query_type,
        "agents_to_run": agents,
        "estimated_tokens": estimated,
    }


def node_supervisor_synthesise(state: ClinicalState, settings: Settings) -> dict:
    """
    Node N: Assemble all agent outputs into a final grounded prompt,
    call the LLM, verify claims with NLI, return ClinicalResponse.
    """
    from src.llm.router import ModelRouter
    from src.llm.prompt_registry import PromptRegistry

    router = ModelRouter(settings)
    registry = PromptRegistry(settings)

    # Assemble context from retrieved chunks
    context_blocks = []
    for i, chunk in enumerate(state["retrieved_chunks"], 1):
        context_blocks.append(
            f"[CHUNK-{i}] (id={chunk.chunk_id}, type={chunk.source_type}, "
            f"time={chunk.timestamp or 'unknown'})\n{chunk.content}"
        )
    context_str = "\n\n".join(context_blocks) if context_blocks else "No clinical records retrieved."

    # Assemble structured summaries from specialist agents
    agent_summaries = []
    if state.get("vitals_analysis"):
        va = state["vitals_analysis"]
        agent_summaries.append(
            f"VITALS ANALYSIS: {va.narrative} "
            f"(anomaly_score={va.anomaly_score:.2f}, detected={va.anomaly_detected})"
        )
    if state.get("note_summary"):
        ns = state["note_summary"]
        agent_summaries.append(f"NOTE SUMMARY ({ns.time_window_hours}h): {ns.summary}")
    if state.get("deterioration_assessment"):
        da = state["deterioration_assessment"]
        agent_summaries.append(
            f"DETERIORATION ASSESSMENT: NEWS2={da.news2.total_score} "
            f"({da.news2.risk_level.value} risk). {da.risk_narrative}"
        )

    # Get versioned prompts from registry
    prompt_name = "clinical-synthesis"
    prompt_version, system_prompt = registry.get_prompt(prompt_name)

    # Build user prompt
    user_prompt = f"""CLINICAL CONTEXT:
{context_str}

SPECIALIST AGENT SUMMARIES:
{chr(10).join(agent_summaries) if agent_summaries else "None"}

PATIENT QUERY:
{state['query']}

Remember: Answer ONLY from the context above. Cite chunk IDs as [CHUNK-N].
If the answer cannot be determined from the context, say so explicitly."""

    # Route to the right model
    model_id = router.route(
        estimated_tokens=state["estimated_tokens"],
        query_type=state["query_type"],
    )

    logger.info(f"[{state['trace_id']}] Synthesis call → model={model_id}")

    # LLM call (simplified — full implementation uses langchain_openai)
    answer, raw_citations = _call_llm(
        model_id=model_id,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        settings=settings,
        trace_id=state["trace_id"],
    )

    # Map citation references back to actual chunks
    cited_chunks = _resolve_citations(raw_citations, state["retrieved_chunks"])

    # NLI verification of key claims (simplified — full impl calls HF sidecar)
    cited_claims = _verify_claims(answer, cited_chunks, settings)

    response = ClinicalResponse(
        answer=answer,
        citations=cited_chunks,
        cited_claims=cited_claims,
        agents_used=state["agents_to_run"],
        model_used=model_id,
        prompt_version=prompt_version,
        trace_id=state["trace_id"],
        insufficient_data=len(cited_chunks) == 0,
    )

    return {
        "final_response": response,
        "model_to_use": model_id,
        "prompt_version": prompt_version,
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
    }


def _call_llm(
    model_id: str,
    system_prompt: str,
    user_prompt: str,
    settings: Settings,
    trace_id: str,
) -> tuple[str, list[str]]:
    """
    Call the appropriate LLM and return (answer, list_of_chunk_refs).
    In production: uses langchain_openai with structured output + Langfuse tracing.
    """
    from langchain_openai import AzureChatOpenAI
    from langchain_core.messages import HumanMessage, SystemMessage
    from langchain_core.output_parsers import JsonOutputParser

    deployment = (
        settings.azure_openai_deployment_gpt4o
        if "gpt-4o" in model_id and "mini" not in model_id
        else settings.azure_openai_deployment_gpt4o_mini
    )

    llm = AzureChatOpenAI(
        azure_deployment=deployment,
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_key,
        api_version=settings.azure_openai_api_version,
        temperature=0.1,
        max_tokens=1024,
    )

    structured_prompt = user_prompt + (
        "\n\nRespond in JSON: "
        '{"answer": "...", "citations": ["CHUNK-1", "CHUNK-3"], "insufficient_data": false}'
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=structured_prompt),
    ]

    import json
    response = llm.invoke(messages)
    try:
        parsed = json.loads(response.content)
        return parsed.get("answer", response.content), parsed.get("citations", [])
    except (json.JSONDecodeError, AttributeError):
        return str(response.content), []


def _resolve_citations(
    raw_refs: list[str],
    chunks: list[RetrievedChunk],
) -> list[RetrievedChunk]:
    """Map CHUNK-N references back to actual RetrievedChunk objects."""
    chunk_map = {f"CHUNK-{i+1}": chunk for i, chunk in enumerate(chunks)}
    cited = []
    for ref in raw_refs:
        if ref in chunk_map and chunk_map[ref] not in cited:
            cited.append(chunk_map[ref])
    return cited


def _verify_claims(
    answer: str,
    cited_chunks: list[RetrievedChunk],
    settings: Settings,
) -> list[CitedClaim]:
    """
    Basic claim extraction + NLI verification.
    Splits answer into sentences and verifies each against its nearest cited chunk.
    Full implementation calls the HF sidecar /nli/batch endpoint.
    """
    import re
    sentences = re.split(r"(?<=[.!?])\s+", answer.strip())
    claims = []
    for sentence in sentences[:5]:  # limit to first 5 claims
        if len(sentence) < 20:
            continue
        chunk = cited_chunks[0] if cited_chunks else None
        claims.append(CitedClaim(
            claim=sentence,
            chunk_id=chunk.chunk_id if chunk else "none",
            entailment_score=0.0,   # populated by HF sidecar in full impl
            verdict="unverified",    # set to pass/warn/fail after NLI call
        ))
    return claims


# ── Graph builder ─────────────────────────────────────────────────

def build_graph(settings: Settings) -> StateGraph:
    """
    Construct and compile the LangGraph StateGraph.

    Graph topology:
        START → supervisor_route → [specialist agents] → supervisor_synthesise → END

    Agents run sequentially in the order decided by the supervisor.
    For parallel execution, use Send() API in LangGraph 0.2+.
    """
    from src.agents.vitals_analyst import node_vitals_analyst
    from src.agents.note_summarizer import node_note_summarizer
    from src.agents.evidence_retrieval import node_evidence_retrieval
    from src.agents.deterioration import node_deterioration

    graph = StateGraph(ClinicalState)

    # Register all nodes
    graph.add_node("supervisor_route", node_supervisor_route)
    graph.add_node("vitals_analyst", lambda s: node_vitals_analyst(s, settings))
    graph.add_node("note_summarizer", lambda s: node_note_summarizer(s, settings))
    graph.add_node("evidence_retrieval", lambda s: node_evidence_retrieval(s, settings))
    graph.add_node("deterioration", lambda s: node_deterioration(s, settings))
    graph.add_node("supervisor_synthesise", lambda s: node_supervisor_synthesise(s, settings))

    # Entry point
    graph.add_edge(START, "supervisor_route")

    # Conditional routing: supervisor decides which agents run
    def route_to_agents(state: ClinicalState) -> list[str]:
        agent_node_map = {
            AgentName.VITALS_ANALYST: "vitals_analyst",
            AgentName.NOTE_SUMMARIZER: "note_summarizer",
            AgentName.EVIDENCE_RETRIEVAL: "evidence_retrieval",
            AgentName.DETERIORATION: "deterioration",
        }
        return [agent_node_map[a] for a in state["agents_to_run"] if a in agent_node_map]

    graph.add_conditional_edges("supervisor_route", route_to_agents)

    # All agents converge to synthesis
    for agent_node in ["vitals_analyst", "note_summarizer", "evidence_retrieval", "deterioration"]:
        graph.add_edge(agent_node, "supervisor_synthesise")

    graph.add_edge("supervisor_synthesise", END)

    return graph.compile()

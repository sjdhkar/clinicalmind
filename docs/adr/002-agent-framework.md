# ADR-002: LangGraph over AutoGen and Semantic Kernel for Agent Orchestration

**Status:** Accepted  
**Date:** 2025-05  
**Deciders:** Srujan Dharkar

---

## Context

ClinicalMind requires a multi-agent orchestration layer with four specialised agents (VitalsAnalyst, NoteSummarizer, EvidenceRetrieval, DeteriorationDetector) coordinated by a supervisor. The orchestration framework needs to support:

- Explicit state management across agent hops
- Conditional routing based on query classification
- Parallel agent execution where safe
- Reproducible, testable agent graphs
- Langfuse tracing integration

Frameworks evaluated: **Microsoft AutoGen**, **Microsoft Semantic Kernel (Agent Framework)**, **LangGraph**, **CrewAI**.

---

## Decision

We use **LangGraph 0.2** for all agent orchestration in the Python AI service.

---

## Rationale

### Typed, explicit state
LangGraph's `StateGraph` requires a typed `TypedDict` or Pydantic model as the shared state object. Every agent reads from and writes to this typed state. This means:
- State transitions are testable in isolation (mock the state, assert the output)
- No implicit "agent memory" or hidden side effects
- Serialisable state for checkpoint/resume (important for long-running clinical queries)

AutoGen and CrewAI both use conversational message passing as state — harder to type, harder to test, harder to inspect.

### Conditional routing
LangGraph's `add_conditional_edges` lets the supervisor route to the correct specialist agent based on query intent classification. The routing logic is explicit Python — not a prompt asking an LLM to decide which tool to call next.

### Python ecosystem integration
The AI service uses LlamaIndex (RAG), RAGAS (evaluation), HuggingFace Transformers, and Langfuse (tracing). All of these have first-class Python integrations. LangGraph is native Python with no framework-imposed constraints on what code runs inside a node.

### Why not Semantic Kernel?
Semantic Kernel is excellent on .NET and is used in the API Gateway layer for LLM abstraction. However:
- The Python Semantic Kernel agent framework is still maturing (as of mid-2025)
- SK's process framework doesn't have LangGraph's level of graph control (conditional edges, cycles, checkpointing)
- Mixing SK and LangGraph would mean two agent runtimes — we keep a clean boundary: SK for the .NET gateway, LangGraph for the Python AI service

### Why not AutoGen?
AutoGen's conversational model is a poor fit for a deterministic clinical pipeline. We don't want agents "chatting" to negotiate a result — we want an explicit graph with typed handoffs and a deterministic execution path for auditability.

---

## Tradeoffs Accepted

| Tradeoff | Mitigation |
|----------|-----------|
| LangGraph adds ~30ms overhead per graph execution vs. direct LLM call | Acceptable — the RAG retrieval and reranking dominate latency |
| LangGraph is Python-only | Clean service boundary: .NET gateway calls Python AI service over HTTP/2 |
| Graph definition requires upfront design | Benefit: the graph IS the documentation of the agent flow |

---

## Consequences

- All agents are implemented as LangGraph nodes with typed input/output contracts
- The `ClinicalState` Pydantic model is the single source of truth for what has been computed in a query lifecycle
- Unit tests for each agent node use mocked state objects — no LLM required for node logic tests
- Langfuse trace IDs are propagated through the LangGraph state for end-to-end observability

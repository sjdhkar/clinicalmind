# System Architecture

## Overview

ClinicalMind follows a clean four-layer architecture with strict separation of concerns and a single trust boundary at the .NET API Gateway.

## Layer Summary

| Layer | Runtime | Responsibility |
|-------|---------|---------------|
| Frontend | Angular 19 on Azure Static Web Apps | UI, streaming, visualisation |
| API Gateway | .NET 10 on AKS | Auth, rate limiting, routing, audit |
| AI Orchestration | Python FastAPI + LangGraph on Container Apps | Agents, RAG, LLMOps |
| Data + Infra | Azure PaaS | Storage, messaging, observability |

## Key Design Decisions

- The API Gateway is the **only entry point** — no AI service is exposed directly
- The HuggingFace sidecar runs in a **private network** — no PHI leaves the Azure tenant
- **Event-driven real-time updates** via Azure Service Bus — observation events trigger agent pipelines asynchronously, not via user-initiated requests
- **Semantic caching** in Redis reduces LLM calls by ~34% for repeated clinical queries

## Data Flow — User Query

```
User types query in Angular UI
        ↓
Angular sends POST /api/chat (with SSE connection open)
        ↓
.NET Gateway: validates JWT, checks rate limit, writes audit record
        ↓
.NET Gateway: forwards to Python AI Orchestrator via HTTP/2
        ↓
LangGraph Supervisor classifies query intent → routes to agent(s)
        ↓
Agent(s) run:
  - Metadata pre-filter on pgvector (patient_id + time window)
  - Hybrid retrieval (pgvector dense + pg_bm25 sparse, RRF merge)
  - Cross-encoder reranking (top 20 → top 5)
  - HuggingFace tasks (NER, Table QA, Chronos) if applicable
  - LLM synthesis call (routed model)
  - NLI claim verification
        ↓
Supervisor assembles final response with citations
        ↓
Response streams back via SSE to Angular UI (token by token)
        ↓
Angular renders tokens progressively, citation badges appear inline
```

## Data Flow — Real-time Observation Event

```
New observation written to EHR (OpenEHR REST adapter)
        ↓
Azure Service Bus receives observation event
        ↓
.NET Gateway IHostedService consumes event
        ↓
Triggers VitalsAnalystAgent + DeteriorationAgent asynchronously
        ↓
Risk score computed (NEWS2 + LLM scoring)
        ↓
Score pushed to patient dashboard via SignalR
        ↓
Ward dashboard updates within ~4 seconds of observation event
```

## C4 Model

Full C4 model diagrams (Context, Container, Component level) are generated using [Structurizr](https://structurizr.com/) from the DSL in `architecture/structurizr.dsl`.

_To render locally:_
```bash
docker run -it --rm -p 8080:8080 structurizr/lite
# Open http://localhost:8080 and load structurizr.dsl
```

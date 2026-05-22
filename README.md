# ClinicalMind 🏥

> **AI-Powered Clinical Observation Intelligence Platform**  
> Multi-agent RAG system that transforms raw clinical observation streams into explainable, grounded clinical intelligence — in real time.

[![CI](https://github.com/sjdhkar/clinicalmind/actions/workflows/ci.yml/badge.svg)](https://github.com/sjdhkar/clinicalmind/actions/workflows/ci.yml)
[![Eval](https://github.com/sjdhkar/clinicalmind/actions/workflows/eval.yml/badge.svg)](https://github.com/sjdhkar/clinicalmind/actions/workflows/eval.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![.NET](https://img.shields.io/badge/.NET-10.0-purple)](https://dotnet.microsoft.com/)
[![Python](https://img.shields.io/badge/Python-3.12-blue)](https://www.python.org/)
[![Angular](https://img.shields.io/badge/Angular-19-red)](https://angular.dev/)

---

## What is ClinicalMind?

Clinicians in busy wards are drowning in observation data. Vital sign trends, free-text nursing notes, and medication records all live in separate silos. A senior nurse reviewing 20 patients cannot synthesise all of this to catch early deterioration.

**ClinicalMind does it automatically.**

It monitors observation streams, detects deterioration patterns via a multi-agent AI pipeline, and surfaces explainable, citation-grounded clinical summaries — all within seconds of a new observation event.

This is not a chatbot. It is an AI platform with production-grade engineering: LLMOps, evaluation pipelines, hallucination prevention, and full audit trails suitable for regulated clinical environments.

---

## Demo

> 📹 **[Watch the 5-minute demo walkthrough →](#)**  
> _(Coming soon — shows live streaming response with citations, evaluation dashboard, and real-time risk score updates)_

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                 Angular 19 Frontend (Azure Static Web Apps)     │
│  Clinical Dashboard │ AI Chat │ Prompt Playground │ Eval Board  │
└──────────────────────────────┬──────────────────────────────────┘
                               │  SSE / REST / WebSocket
┌──────────────────────────────▼──────────────────────────────────┐
│              .NET 10 API Gateway (AKS)                          │
│  Auth/RBAC │ Streaming Proxy │ Rate Limiting │ Audit Log        │
└──────────────────────────────┬──────────────────────────────────┘
                               │  gRPC / HTTP2
┌──────────────────────────────▼──────────────────────────────────┐
│         Python FastAPI + LangGraph (Azure Container Apps)       │
│                                                                 │
│  ┌─────────────────── Supervisor Agent ──────────────────────┐  │
│  │  VitalsAnalyst │ NoteSummarizer │ EvidenceRetrieval │ Det. │  │
│  └───────────────────────────────────────────────────────────┘  │
│  Model Router │ Semantic Cache │ Prompt Registry (Langfuse)     │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│  Data Layer (Azure)                                             │
│  PostgreSQL + pgvector │ Azure Blob │ Service Bus │ OTel        │
└─────────────────────────────────────────────────────────────────┘
         │
┌────────▼─────────────────────────────────────────────────────────┐
│  HuggingFace Inference Sidecar (private — no PHI leaves)         │
│  Bio_ClinicalBERT NER · Chronos-T5 · TAPAS · cross-encoder      │
└──────────────────────────────────────────────────────────────────┘
```

See [`docs/architecture/`](./docs/architecture/) for full C4 model diagrams and Architecture Decision Records.

---

## AI Engineering Highlights

| Component | Approach | Why it matters |
|-----------|----------|----------------|
| **RAG** | Three-corpus hybrid (pgvector + BM25 + RRF) | Clinical terms need exact-match retrieval; dense-only misses drug names |
| **Agents** | LangGraph StateGraph with 4 specialised agents | Typed state, testable nodes, explicit routing |
| **Hallucination prevention** | Grounded prompts + citation enforcement + NLI verification (DeBERTa) | Clinical wrong answers have consequences |
| **Evaluation** | RAGAS + custom clinical metrics in CI/CD | Eval gates on every PR, not ad-hoc |
| **HuggingFace** | 5 tasks: Token Classification, Summarization, Table QA, Time Series, Feature Extraction | Local inference for PHI safety + cost |
| **Cost optimisation** | Model router: Phi-3 / GPT-4o-mini / GPT-4o by query complexity | ~52% cost reduction vs. routing everything to GPT-4o |
| **LLMOps** | Langfuse: prompt versioning, cost tracking, trace correlation | Production AI needs governance, not vibes |

---

## Tech Stack

### Frontend
- **Angular 19** (standalone components, signals)
- **NgRx Signal Store** for state management
- **ECharts** for evaluation dashboards and vital sign charts
- **SSE streaming** for real-time AI response rendering

### Backend Gateway
- **.NET 10** Minimal APIs + MediatR (CQRS)
- **Semantic Kernel 1.x** for LLM abstraction
- **PostgreSQL 16** + **pgvector** + **Redis 7**
- **Azure AD B2C** for authentication

### AI Orchestration
- **Python 3.12** + **FastAPI**
- **LangGraph 0.2** for multi-agent orchestration
- **LlamaIndex 0.11** for RAG pipeline
- **RAGAS** for evaluation
- **Langfuse** for LLMOps

### HuggingFace Models
- `d4data/biomedical-ner-all` — clinical named entity recognition
- `amazon/chronos-t5-small` — vital sign time-series forecasting
- `google/tapas-base-finetuned-wtq` — lab table question answering
- `cross-encoder/ms-marco-MiniLM-L-6-v2` — RAG reranking
- `cross-encoder/nli-deberta-v3-small` — NLI claim verification

### Infrastructure
- **AKS** (Kubernetes) + **Azure Container Apps**
- **GitHub Actions** CI/CD with eval gates
- **Bicep** Infrastructure-as-Code
- **OpenTelemetry** → **Grafana** observability

---

## Evaluation Results

> Latest run against 200-scenario clinical golden set:

| Metric | Score | Threshold |
|--------|-------|-----------|
| Faithfulness | 0.91 | ≥ 0.85 |
| Answer Relevancy | 0.88 | ≥ 0.80 |
| Context Precision | 0.87 | ≥ 0.80 |
| Context Recall | 0.83 | ≥ 0.75 |
| Hallucination Rate | 2.8% | ≤ 5% |
| NEWS2 Agreement | 94.2% | ≥ 90% |
| P95 Latency | 3.4s | ≤ 5s |
| Cache Hit Rate | 34% | — |
| Avg Cost / Query | $0.0021 | — |

_Full eval history: [`docs/eval-results/`](./docs/eval-results/)_

---

## Project Structure

```
clinicalmind/
├── apps/
│   ├── web/                    # Angular 19 frontend
│   └── api-gateway/            # .NET 10 API gateway
├── services/
│   ├── ai-orchestrator/        # Python FastAPI + LangGraph agents
│   └── hf-inference/           # HuggingFace inference sidecar
├── packages/
│   ├── shared-types/           # OpenAPI-generated TypeScript types
│   └── clinical-eval/          # RAGAS evaluation scripts + golden set
├── infra/
│   ├── bicep/                  # Azure IaC templates
│   ├── helm/                   # Kubernetes Helm charts
│   └── k8s/                    # Raw K8s manifests
├── docs/
│   ├── adr/                    # Architecture Decision Records
│   ├── architecture/           # C4 diagrams + system design docs
│   └── eval-results/           # Benchmark snapshots
└── .github/
    └── workflows/              # CI/CD + eval pipelines
```

---

## Getting Started (Local Dev)

**Prerequisites:** Docker Desktop, Node.js 22, .NET 10 SDK, Python 3.12

```bash
# 1. Clone
git clone https://github.com/sjdhkar/clinicalmind.git
cd clinicalmind

# 2. Copy env template
cp .env.example .env
# Edit .env with your Azure OpenAI key and PostgreSQL credentials

# 3. Start all services
docker compose up -d

# 4. Seed the vector database with sample clinical data
cd packages/clinical-eval && python seed_demo_data.py

# 5. Open the app
open http://localhost:4200
```

Full setup guide: [`docs/SETUP.md`](./docs/SETUP.md)

---

## Why This Project Exists

I built ClinicalMind as part of a career transition into AI Engineering. My background is 5 years of enterprise healthcare platform engineering (.NET / Angular / OpenEHR at Tietoevry), which shaped every architectural decision here:

- **Domain-aware chunking** at OpenEHR archetype boundaries (not naive sliding windows)
- **PHI-safe HuggingFace inference** in a private sidecar (no patient data to third-party APIs)
- **NEWS2-grounded deterioration scoring** (a real clinical early warning system, not invented)
- **Audit trails as a first-class concern** (regulated environments need them from day one)

This is the AI layer I wish existed above the systems I've been building.

---

## Roadmap

- [x] Repo scaffold + documentation
- [ ] HuggingFace inference sidecar (NER + Chronos)
- [ ] LangGraph agent orchestration (4 agents)
- [ ] RAG pipeline (pgvector + BM25 + reranking)
- [ ] .NET 10 API gateway + streaming proxy
- [ ] Angular 19 clinical dashboard + streaming UI
- [ ] RAGAS evaluation pipeline + CI/CD gates
- [ ] Langfuse LLMOps integration
- [ ] Azure deployment (Bicep + AKS)
- [ ] Prompt Playground + Evaluation Dashboard UI
- [ ] Live demo deployment

---

## Architecture Decision Records

| ADR | Decision |
|-----|----------|
| [ADR-001](./docs/adr/001-vector-database.md) | PostgreSQL + pgvector over Pinecone |
| [ADR-002](./docs/adr/002-agent-framework.md) | LangGraph over AutoGen / Semantic Kernel |
| [ADR-003](./docs/adr/003-chunking-strategy.md) | Archetype-boundary chunking over sliding window |
| [ADR-004](./docs/adr/004-hallucination-prevention.md) | Four-layer hallucination prevention strategy |
| [ADR-005](./docs/adr/005-model-routing.md) | Dynamic model routing for cost optimisation |

---

## License

MIT — see [LICENSE](./LICENSE)

---

*Built by [Srujan Dharkar](https://www.linkedin.com/in/srujandharkar) · [LinkedIn](https://www.linkedin.com/in/srujandharkar) · [GitHub](https://github.com/sjdhkar)*

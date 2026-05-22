# AI Orchestrator Service

**Runtime:** Python 3.12 + FastAPI  
**Port:** 8000  
**Responsibility:** LangGraph multi-agent orchestration, RAG pipeline, LLMOps

## Structure (planned)

```
ai-orchestrator/
├── src/
│   ├── agents/
│   │   ├── supervisor.py          # LangGraph StateGraph + router
│   │   ├── vitals_analyst.py      # Chronos anomaly detection + GPT-4o synthesis
│   │   ├── note_summarizer.py     # Bio_ClinicalBERT NER + summarization
│   │   ├── evidence_retrieval.py  # Hybrid RAG pipeline
│   │   └── deterioration.py       # NEWS2 scorer + LLM risk narrative
│   ├── rag/
│   │   ├── chunkers.py            # Archetype / sentence / hierarchical chunkers
│   │   ├── retriever.py           # pgvector + BM25 + RRF + reranker
│   │   └── ingestor.py            # Document ingestion pipeline
│   ├── llm/
│   │   ├── router.py              # Model routing logic
│   │   ├── cache.py               # Redis semantic cache
│   │   └── prompt_registry.py     # Langfuse prompt versioning
│   ├── models/
│   │   └── clinical_state.py      # LangGraph shared state (Pydantic)
│   └── api/
│       ├── main.py                # FastAPI app
│       └── routes/
├── tests/
│   ├── unit/                      # Agent node unit tests (no LLM)
│   └── integration/               # Full pipeline tests
├── pyproject.toml
└── Dockerfile
```

## Status: 🚧 In Development

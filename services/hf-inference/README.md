# HuggingFace Inference Sidecar

**Runtime:** Python 3.12 + FastAPI  
**Port:** 8001  
**Responsibility:** Local HuggingFace model inference — no PHI leaves the Azure tenant

## Models Served

| Endpoint | Model | HF Task | Use in ClinicalMind |
|----------|-------|---------|---------------------|
| `POST /ner` | `d4data/biomedical-ner-all` | Token Classification | Extract clinical entities from nursing notes |
| `POST /timeseries/anomaly` | `amazon/chronos-t5-small` | Time Series Forecasting | Vital sign anomaly detection |
| `POST /table-qa` | `google/tapas-base-finetuned-wtq` | Table Question Answering | Lab result table queries |
| `POST /rerank` | `cross-encoder/ms-marco-MiniLM-L-6-v2` | Sentence Similarity | RAG chunk reranking |
| `POST /nli` | `cross-encoder/nli-deberta-v3-small` | Natural Language Inference | Hallucination claim verification |
| `POST /embed` | `BAAI/bge-small-en-v1.5` | Feature Extraction | Chunk embeddings (local, avoids API cost) |

## Why a Sidecar?

Clinical data is PHI. Sending patient observation text to a third-party inference API (OpenAI, HuggingFace Inference API) creates a data residency concern in regulated environments.

All HuggingFace models run locally inside the Azure private network. Only non-clinical prompts (grounded summaries, already stripped of direct identifiers) are sent to Azure OpenAI.

## Status: 🚧 In Development

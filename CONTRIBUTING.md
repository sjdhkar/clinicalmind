# Contributing to ClinicalMind

ClinicalMind is a portfolio project demonstrating production-grade AI engineering patterns. Contributions, issues, and discussions are welcome.

## Local development setup

```bash
# Prerequisites: Docker Desktop, Node 22, .NET 10 SDK, Python 3.12

git clone https://github.com/sjdhkar/clinicalmind.git
cd clinicalmind
cp .env.example .env   # add your Azure OpenAI key

docker compose up -d   # starts postgres, redis, hf-inference, ai-orchestrator, gateway

cd packages/clinical-eval
python seed_demo_data.py   # seeds 4 demo patients

# Frontend
cd apps/web && npm ci && ng serve
open http://localhost:4200
```

## Project structure

```
services/hf-inference/     # Python — HuggingFace sidecar (6 models)
services/ai-orchestrator/  # Python — LangGraph agents + RAG pipeline
apps/api-gateway/          # C# .NET 10 — SSE proxy + auth + audit
apps/web/                  # Angular 19 — streaming UI + eval dashboard
packages/clinical-eval/    # Python — RAGAS evaluation pipeline
infra/                     # Bicep IaC + Helm charts + DB schema
```

## Making changes

- Each service has its own `pyproject.toml` / `.csproj` / `package.json`
- Unit tests run without any external dependencies (mocked models/LLMs)
- PRs trigger the RAGAS evaluation gate — faithfulness must stay ≥ 0.85

## Architecture decisions

Before making significant changes, read the ADRs in `docs/adr/` — they explain why specific technologies were chosen and what tradeoffs were accepted.

## Code style

- Python: `ruff` (linting) + `mypy` (types)
- C#: standard .NET formatting
- TypeScript: strict mode enabled

## Questions?

Open a GitHub Discussion or reach out via [LinkedIn](https://www.linkedin.com/in/srujandharkar).

# GitHub Repository Setup Guide

Steps to make the repo stand out on first impression.

## 1. Add repo description and topics

Go to https://github.com/sjdhkar/clinicalmind → click the ⚙ gear next to "About"

**Description:**
```
AI-powered clinical observation intelligence platform — multi-agent RAG, LangGraph orchestration, real-time deterioration detection, LLMOps with RAGAS evaluation. .NET 10 · Python · Angular 19 · Azure
```

**Website:** (leave blank until you deploy a demo)

**Topics (add all of these):**
```
ai-engineering  rag  langgraph  langchain  multi-agent
dotnet  aspnet-core  angular  python  fastapi
azure  kubernetes  opentelemetry  llmops  pgvector
huggingface  healthcare  openehr  semantic-kernel  ragas
```

## 2. Pin this repo on your GitHub profile

Go to https://github.com/sjdhkar → Edit profile → Pin repositories → select clinicalmind

## 3. Enable GitHub Actions

Go to https://github.com/sjdhkar/clinicalmind/actions
Click "I understand my workflows, go ahead and enable them"

The CI badge in the README will go green once secrets are configured.

## 4. Add repository secrets for CI

Go to Settings → Secrets and variables → Actions → New repository secret

| Secret name | Value |
|-------------|-------|
| `AZURE_OPENAI_ENDPOINT` | Your Azure OpenAI endpoint URL |
| `AZURE_OPENAI_KEY` | Your Azure OpenAI API key |
| `LANGFUSE_SECRET_KEY` | Your Langfuse secret (optional) |
| `LANGFUSE_PUBLIC_KEY` | Your Langfuse public key (optional) |

Without these, the RAGAS eval job will skip the LLM calls and use heuristic scoring.

## 5. Social preview image

Go to Settings → Social preview → Upload image
Use the file: `docs/social-preview.png` (generated below)

## 6. Enable GitHub Pages for eval dashboard

Go to Settings → Pages → Source: Deploy from branch → Branch: main → Folder: /docs
The eval dashboard at `docs/eval-results/index.html` will publish automatically.

# ADR-005: Dynamic Model Routing for Cost Optimisation

**Status:** Accepted  
**Date:** 2025-05  
**Deciders:** Srujan Dharkar

---

## Context

Routing every query to GPT-4o produces the highest quality but is expensive at scale. A 500-bed hospital generating 5,000 clinical queries/day at GPT-4o pricing (~$0.005/query) costs ~$25/day or ~$750/month. More than half of these queries are simple structured lookups that don't require GPT-4o's reasoning capability.

---

## Decision

Implement a **three-tier model router** that selects the LLM based on query characteristics, with an override mechanism for admin users.

---

## Routing Logic

```python
def route_model(query: ClinicalQuery) -> ModelConfig:
    # Tier 1: Simple structured lookups → local Phi-3-mini
    if (
        query.token_estimate < 500
        and query.query_type in {QueryType.SIMPLE_LOOKUP, QueryType.TABLE_QA}
        and not query.requires_multi_step_reasoning
    ):
        return ModelConfig(model="phi-3-mini", max_tokens=512)

    # Tier 2: Summarization, note analysis → GPT-4o-mini
    elif (
        query.query_type in {QueryType.SUMMARIZATION, QueryType.TREND_ANALYSIS}
        and query.token_estimate < 2000
    ):
        return ModelConfig(model="gpt-4o-mini", max_tokens=1024)

    # Tier 3: Complex reasoning, multi-agent synthesis → GPT-4o
    else:
        return ModelConfig(model="gpt-4o", max_tokens=2048)
```

### Query type classification

Query types are classified by a lightweight `distilbert-base-uncased` text classifier trained on 500 labelled clinical query examples. The classifier runs in <20ms and determines the routing decision before any expensive LLM call.

---

## Cost Impact

Based on evaluation golden set routing distribution:

| Tier | Model | % of queries | Cost/query | Monthly (5k/day) |
|------|-------|-------------|------------|------------------|
| 1 | Phi-3-mini | 38% | ~$0.0000 (local) | $0 |
| 2 | GPT-4o-mini | 41% | ~$0.0004 | $24.60 |
| 3 | GPT-4o | 21% | ~$0.0050 | $157.50 |
| **All GPT-4o baseline** | GPT-4o | 100% | ~$0.0050 | **$750.00** |

**Estimated saving: ~76%** vs. all-GPT-4o routing, with no measurable quality degradation on Tier 1/2 queries (verified via eval golden set).

---

## Quality Safeguards

- Quality evaluation on the golden set is run with each tier's model to ensure Tier 1/2 quality meets threshold
- Any query that fails quality thresholds at Tier 1/2 is automatically escalated to the next tier (one retry allowed)
- The routing decision and model used are logged in the audit trail on every query

---

## Consequences

- Model routing decisions are configurable via the Admin panel without redeployment
- Phi-3-mini runs as part of the HuggingFace inference sidecar (same container, no extra infrastructure)
- RAGAS evaluation must run per-tier to validate quality at each routing level
- A "force GPT-4o" override is available to admin users for critical queries

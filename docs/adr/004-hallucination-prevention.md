# ADR-004: Four-Layer Hallucination Prevention Strategy

**Status:** Accepted  
**Date:** 2025-05  
**Deciders:** Srujan Dharkar

---

## Context

ClinicalMind generates AI-assisted clinical summaries and answers clinical questions. A hallucinated answer in a clinical context — inventing a medication the patient isn't taking, fabricating a lab value — is not a UX bug. It is a patient safety concern.

Single-layer hallucination prevention (e.g., "just add grounding instructions to the prompt") is insufficient for a regulated domain.

---

## Decision

We implement **four independent hallucination prevention layers**, each of which can catch failures the others miss.

---

## Layers

### Layer 1: Grounded prompt construction

Every LLM call uses a prompt template that explicitly constrains the response to the retrieved context:

```
Answer the clinical question using ONLY the information in the context below.
If the answer cannot be found in the context, respond with:
{"answer": "Insufficient data in the available records to answer this question.", "citations": []}

Do not use any prior knowledge. Do not invent values, medications, or clinical events.
```

This is the cheapest layer — it costs nothing but prompt tokens.

### Layer 2: Structured output with mandatory citations

The LLM response schema (enforced via function calling / structured output) requires:

```python
class ClinicalResponse(BaseModel):
    answer: str
    citations: List[ChunkId]  # must reference actual retrieved chunk IDs
    confidence: Literal["high", "medium", "low"]
    insufficient_data: bool
```

Responses that fail schema validation are rejected and retried. Responses with `citations: []` and `insufficient_data: false` are flagged for review — the LLM is claiming certainty with no evidence.

### Layer 3: NLI claim verification

Each factual claim in the response is verified against its cited chunk using a Natural Language Inference model (`cross-encoder/nli-deberta-v3-small`):

- Claims with entailment score ≥ 0.7 → **pass**
- Claims with entailment score 0.4–0.69 → **flagged** (shown with a ⚠ indicator in the UI)
- Claims with entailment score < 0.4 → **blocked** (response is not shown; fallback is triggered)

This catches cases where the LLM cites a chunk but makes a claim not actually supported by it.

### Layer 4: Immutable audit trail

Every LLM call records to an append-only audit table:

```sql
CREATE TABLE ai_audit (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  trace_id UUID NOT NULL,
  patient_id UUID,
  agent_name TEXT NOT NULL,
  prompt_version TEXT NOT NULL,
  model_id TEXT NOT NULL,
  retrieved_chunk_ids UUID[] NOT NULL,
  response_hash TEXT NOT NULL,  -- SHA-256 of response text
  nli_scores JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

This layer doesn't prevent hallucinations — it ensures every AI output is reproducible and auditable after the fact. A clinician or regulator can reconstruct exactly what evidence the AI used for any historical statement.

---

## Consequences

- Layer 3 (NLI) adds ~180ms per response (DeBERTa inference on CPU)
- The UI exposes Layer 3 scores in the "Why did it say this?" explainability panel
- Layer 2 schema validation handles ~3% of responses that require a retry
- The combination of Layers 1–3 produces a measured hallucination rate of 2.8% on the evaluation golden set

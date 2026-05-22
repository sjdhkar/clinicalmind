# ADR-003: Archetype-Boundary Chunking over Sliding Window

**Status:** Accepted  
**Date:** 2025-05  
**Deciders:** Srujan Dharkar

---

## Context

The RAG pipeline needs to chunk clinical data from three sources into vector-store documents:
1. OpenEHR observation archetypes (structured — vitals, lab results, medication records)
2. Free-text nursing notes and clinical assessments
3. Protocol PDFs (NICE guidelines, hospital procedures)

The naive approach — fixed-size sliding window with overlap — is the default in most RAG tutorials. We evaluated it against domain-aware alternatives.

---

## Decision

We use **three different chunking strategies** depending on source data type, not a single universal chunker.

---

## Rationale

### Structured observations: archetype-boundary chunking

Each OpenEHR archetype instance (e.g. one blood pressure reading, one NEWS2 score) is treated as a single chunk. The chunk body is the JSON serialisation of the archetype, and the chunk metadata includes:

```json
{
  "archetype_id": "openEHR-EHR-OBSERVATION.blood_pressure.v2",
  "patient_id": "...",
  "encounter_id": "...",
  "timestamp": "2025-05-22T14:32:00Z",
  "author_role": "nurse",
  "chunk_type": "observation"
}
```

**Why:** A blood pressure reading split across two chunks destroys its meaning. Systolic and diastolic are part of one clinical concept — they must be retrieved together. Sliding window chunking doesn't know this. Archetype boundary chunking does, because OpenEHR's data model already encodes the semantic unit.

### Free-text notes: sentence-level with 2-sentence overlap

Nursing notes are chunked at sentence boundaries (using spaCy's `en_core_sci_sm` sentenciser) with a 2-sentence overlap. Timestamp, author role, and note type (admission, handover, incident) are preserved as metadata.

**Why:** Sentence boundaries in clinical text are meaningful. "Patient appeared comfortable" and "SpO2 dropped to 91%" are different observations that may retrieve separately. Fixed-size chunking often splits mid-sentence and mid-thought. The 2-sentence overlap ensures context around entity mentions isn't lost.

### Protocol PDFs: hierarchical chunking (parent + child)

Protocol PDFs (NICE guidelines, hospital procedures) use a hierarchical strategy:
- **Parent chunks:** section-level (heading + all content under it) — stored but not embedded
- **Child chunks:** paragraph-level — embedded and indexed

Retrieval returns the child chunk. Context assembly includes the parent chunk header to provide section framing.

**Why:** A paragraph about "Management of sepsis — fluid resuscitation" is only interpretable in the context of its section. Without the parent, the LLM doesn't know if this is a paediatric protocol or an adult one. Hierarchical chunking preserves that context without bloating the embedding input.

---

## Sliding Window Rejected

Fixed-size sliding window (e.g., 512 tokens, 50-token overlap) was prototyped and evaluated:

- Blood pressure readings were split: chunk A had systolic, chunk B had diastolic. The retriever returned chunk A for "what was the patient's BP?" and the LLM answered with only the systolic value. **Clinical safety concern.**
- Archetype metadata (patient_id, timestamp) was duplicated across every overlapping chunk, inflating index size by ~40%.
- Semantic coherence score (measured via RAGAS context precision) was 0.61 for sliding window vs 0.87 for archetype-boundary. A 26-point difference on a clinical task is not acceptable.

---

## Consequences

- The ingestion pipeline requires source-type detection before chunking
- Three separate LlamaIndex `NodeParser` implementations: `ArchetypeNodeParser`, `ClinicalSentenceNodeParser`, `HierarchicalNodeParser`
- Chunk metadata schema is enforced via Pydantic — missing metadata fields fail at ingestion, not at retrieval
- Retrieval pre-filtering on `chunk_type` and `patient_id` narrows the search space before ANN search runs

# ADR-001: PostgreSQL + pgvector over a Dedicated Vector Database

**Status:** Accepted  
**Date:** 2025-05  
**Deciders:** Srujan Dharkar

---

## Context

ClinicalMind needs a vector store for three RAG corpora:
1. Per-patient observation chunks (ephemeral, high write frequency)
2. Clinical knowledge base — NICE guidelines, protocol PDFs (low write, high read)
3. Evaluation golden set (read-only)

The options evaluated were: **Pinecone**, **Weaviate**, **Qdrant**, and **PostgreSQL + pgvector**.

---

## Decision

We use **PostgreSQL 16 with the pgvector extension** as the primary vector store, supplemented by **pg_bm25 (ParadeDB)** for BM25 sparse retrieval.

---

## Rationale

### Data residency and PHI compliance
Clinical data is regulated. Using a managed cloud vector database (Pinecone, Weaviate Cloud) means patient-derived embeddings leave the Azure tenant boundary. PostgreSQL runs inside our Azure Database for PostgreSQL Flexible Server — same boundary as the rest of patient data.

### Operational simplicity
We already operate PostgreSQL for the relational data model (audit logs, user management, prompt registry). Adding pgvector is a single `CREATE EXTENSION vector` — not an additional managed service, billing account, or network hop.

### Transactional consistency
Patient chunks need to be written atomically with their metadata (patient_id, encounter_id, archetype_id, timestamp). PostgreSQL ACID transactions give us this for free. Pinecone's metadata filtering is eventually consistent and cannot be wrapped in a transaction with relational writes.

### Hybrid retrieval in a single query
With pgvector + pg_bm25, a hybrid dense + sparse retrieval query runs as a single SQL statement with RRF scoring. With separate vector and search services, this requires two network round-trips, two result sets, and application-layer merging.

### Cost
pgvector is free. Pinecone at the scale of 10M vectors (one patient population) costs ~$70/month. For a portfolio project with potential production path, operational cost matters.

---

## Tradeoffs Accepted

| Tradeoff | Mitigation |
|----------|-----------|
| pgvector doesn't scale beyond ~100M vectors as well as Pinecone | Acceptable for this use case; hospital patient populations don't approach this |
| No native multitenancy isolation in pgvector | Enforced via `patient_id` and `namespace` metadata columns with row-level security |
| HNSW index rebuild needed after bulk inserts | Scheduled during low-traffic maintenance windows |
| No managed filtering push-down as sophisticated as Weaviate | Implemented as a two-stage filter: SQL WHERE clause pre-filter, then pgvector ANN search on filtered set |

---

## Alternatives Rejected

**Pinecone:** Excellent scalability, but PHI data residency is unacceptable. Also introduces a second billing surface and network dependency.

**Weaviate:** Strong hybrid search story, but self-hosting complexity on Kubernetes is non-trivial for a solo project. The operational overhead outweighs the feature benefit at this scale.

**Qdrant:** Technically excellent (Rust, fast, good filtering). Rejected for the same operational-simplicity reason as Weaviate — another service to operate, monitor, and scale.

---

## Consequences

- All vector operations go through the existing PostgreSQL connection pool (pgBouncer)
- Hybrid retrieval is implemented using `pgvector` cosine similarity + `pg_bm25` BM25 scores merged with Reciprocal Rank Fusion in SQL
- A migration path to Qdrant or Pinecone is documented if vector counts exceed 50M

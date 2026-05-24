-- ============================================================
-- ClinicalMind PostgreSQL schema
-- Run automatically by Docker when the postgres container starts
-- (mounted at /docker-entrypoint-initdb.d/init.sql)
-- ============================================================

-- Extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- trigram search for BM25 fallback

-- ── Schemas ──────────────────────────────────────────────────────
CREATE SCHEMA IF NOT EXISTS clinical;
CREATE SCHEMA IF NOT EXISTS audit;
CREATE SCHEMA IF NOT EXISTS eval;

-- ============================================================
-- clinical.chunks — RAG vector store
-- One row per clinical text chunk (observation / note / protocol)
-- ============================================================
CREATE TABLE IF NOT EXISTS clinical.chunks (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id      UUID        NOT NULL,
    encounter_id    UUID        NOT NULL,
    content         TEXT        NOT NULL,
    source_type     TEXT        NOT NULL CHECK (source_type IN ('observation', 'nursing_note', 'protocol')),
    archetype_id    TEXT,
    author_role     TEXT,
    timestamp       TIMESTAMPTZ,
    embedding       VECTOR(384) NOT NULL,   -- BGE-small-en-v1.5 dimension
    metadata        JSONB       DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    expires_at      TIMESTAMPTZ             -- NULL = persistent (protocols); set for patient chunks
);

-- Indexes for hybrid retrieval
-- 1. ANN index (HNSW) for dense vector search
CREATE INDEX IF NOT EXISTS idx_chunks_embedding
    ON clinical.chunks USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- 2. Composite index for metadata pre-filter (applied BEFORE ANN search)
CREATE INDEX IF NOT EXISTS idx_chunks_patient_encounter
    ON clinical.chunks (patient_id, encounter_id, source_type, created_at DESC);

-- 3. TTL cleanup index
CREATE INDEX IF NOT EXISTS idx_chunks_expires
    ON clinical.chunks (expires_at)
    WHERE expires_at IS NOT NULL;

-- 4. GIN trigram index for BM25-style keyword search (pg_trgm fallback)
CREATE INDEX IF NOT EXISTS idx_chunks_content_trgm
    ON clinical.chunks USING gin (content gin_trgm_ops);

-- ============================================================
-- clinical.observations — raw OpenEHR observation archetypes
-- Source data before chunking; used for NEWS2 calculation
-- ============================================================
CREATE TABLE IF NOT EXISTS clinical.observations (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id      UUID        NOT NULL,
    encounter_id    UUID        NOT NULL,
    archetype_id    TEXT        NOT NULL,
    data            JSONB       NOT NULL,   -- raw archetype JSON
    recorded_by     TEXT,
    recorded_at     TIMESTAMPTZ NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_obs_patient_time
    ON clinical.observations (patient_id, encounter_id, recorded_at DESC);

CREATE INDEX IF NOT EXISTS idx_obs_archetype
    ON clinical.observations (archetype_id, patient_id);

-- ============================================================
-- audit.records — immutable AI audit trail
-- Every AI-assisted action is written here and never updated
-- ============================================================
CREATE TABLE IF NOT EXISTS audit.records (
    id              UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    trace_id        TEXT        NOT NULL,
    user_id         TEXT        NOT NULL,
    patient_id      UUID,
    encounter_id    UUID,
    endpoint        TEXT        NOT NULL,
    method          TEXT        NOT NULL,
    status_code     INT,
    elapsed_ms      NUMERIC(10,2),
    agent_name      TEXT,
    model_used      TEXT,
    prompt_version  TEXT,
    query_hash      TEXT,       -- SHA-256 of query (not the query itself — PII)
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Audit table is append-only: revoke UPDATE and DELETE from the app user
REVOKE UPDATE, DELETE ON audit.records FROM PUBLIC;

CREATE INDEX IF NOT EXISTS idx_audit_trace   ON audit.records (trace_id);
CREATE INDEX IF NOT EXISTS idx_audit_patient ON audit.records (patient_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_user    ON audit.records (user_id, created_at DESC);

-- ============================================================
-- eval.runs — RAGAS evaluation history
-- Written by the nightly eval CI job
-- ============================================================
CREATE TABLE IF NOT EXISTS eval.runs (
    id                  UUID    PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_date            DATE    NOT NULL DEFAULT CURRENT_DATE,
    git_sha             TEXT,
    prompt_version      TEXT,
    scenario_count      INT     NOT NULL,
    faithfulness        NUMERIC(5,4),
    answer_relevancy    NUMERIC(5,4),
    context_precision   NUMERIC(5,4),
    context_recall      NUMERIC(5,4),
    hallucination_rate  NUMERIC(5,4),
    news2_agreement     NUMERIC(5,4),
    p95_latency_ms      NUMERIC(10,2),
    avg_cost_usd        NUMERIC(10,6),
    cache_hit_rate      NUMERIC(5,4),
    passed_thresholds   BOOLEAN NOT NULL DEFAULT FALSE,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_eval_date ON eval.runs (run_date DESC);

-- ============================================================
-- eval.scenario_results — per-scenario eval detail
-- ============================================================
CREATE TABLE IF NOT EXISTS eval.scenario_results (
    id              UUID    PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_id          UUID    NOT NULL REFERENCES eval.runs(id) ON DELETE CASCADE,
    scenario_id     TEXT    NOT NULL,
    question        TEXT    NOT NULL,
    expected_answer TEXT    NOT NULL,
    actual_answer   TEXT,
    faithfulness    NUMERIC(5,4),
    relevancy       NUMERIC(5,4),
    passed          BOOLEAN,
    model_used      TEXT,
    latency_ms      NUMERIC(10,2),
    cost_usd        NUMERIC(10,6)
);

CREATE INDEX IF NOT EXISTS idx_scenario_run ON eval.scenario_results (run_id);

-- ============================================================
-- llm.prompt_versions — local prompt registry
-- (Langfuse is primary; this is the fallback + audit trail)
-- ============================================================
CREATE SCHEMA IF NOT EXISTS llm;

CREATE TABLE IF NOT EXISTS llm.prompt_versions (
    id              UUID    PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            TEXT    NOT NULL,
    version         TEXT    NOT NULL,
    system_prompt   TEXT    NOT NULL,
    changelog       TEXT,
    is_active       BOOLEAN DEFAULT FALSE,
    eval_score      NUMERIC(5,4),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (name, version)
);

CREATE INDEX IF NOT EXISTS idx_prompt_name ON llm.prompt_versions (name, is_active);

-- ============================================================
-- Seed: initial prompt versions
-- ============================================================
INSERT INTO llm.prompt_versions (name, version, system_prompt, changelog, is_active)
VALUES (
    'clinical-synthesis', 'v1.2.0',
    'You are ClinicalMind, an AI clinical decision support assistant.
Answer ONLY from the context provided. Cite every factual claim with [CHUNK-N].
If the answer cannot be found, respond: "Insufficient data in the available records."
Never invent clinical values. Respond in JSON: {"answer":"...","citations":["CHUNK-1"],"insufficient_data":false}',
    'Initial production prompt',
    TRUE
)
ON CONFLICT (name, version) DO NOTHING;

-- ============================================================
-- Maintenance: TTL cleanup function
-- Run nightly via pg_cron or a scheduled job
-- ============================================================
CREATE OR REPLACE FUNCTION clinical.cleanup_expired_chunks()
RETURNS INTEGER AS $$
DECLARE deleted_count INTEGER;
BEGIN
    DELETE FROM clinical.chunks
    WHERE expires_at IS NOT NULL AND expires_at < NOW();
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Done
DO $$ BEGIN
    RAISE NOTICE 'ClinicalMind schema initialised successfully';
    RAISE NOTICE 'Schemas: clinical, audit, eval, llm';
    RAISE NOTICE 'Tables: 7 | Indexes: 11 | Extensions: vector, uuid-ossp, pg_trgm';
END $$;

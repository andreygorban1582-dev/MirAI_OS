-- MirAI Context Storage – PostgreSQL initialisation
-- Enables pgvector and creates core tables for rolling context + knowledge base

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ─── Session context (rolling window) ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS context_messages (
    id          BIGSERIAL PRIMARY KEY,
    session_id  TEXT        NOT NULL,
    role        TEXT        NOT NULL CHECK (role IN ('system','user','assistant')),
    content     TEXT        NOT NULL,
    tokens      INT         DEFAULT 0,
    embedding   VECTOR(384),
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ctx_session ON context_messages (session_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ctx_embedding ON context_messages USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- ─── Long-term knowledge base (offline Wikipedia / history etc.) ───────────────
CREATE TABLE IF NOT EXISTS knowledge_base (
    id          BIGSERIAL PRIMARY KEY,
    source      TEXT        NOT NULL,
    title       TEXT,
    content     TEXT        NOT NULL,
    embedding   VECTOR(384),
    metadata    JSONB       DEFAULT '{}',
    indexed_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_kb_source   ON knowledge_base (source);
CREATE INDEX IF NOT EXISTS idx_kb_title    ON knowledge_base USING gin (title gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_kb_embedding ON knowledge_base USING ivfflat (embedding vector_cosine_ops) WITH (lists = 200);

-- ─── Persona memory ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS persona_memory (
    id          BIGSERIAL PRIMARY KEY,
    persona     TEXT        NOT NULL,
    memory_key  TEXT        NOT NULL,
    memory_val  TEXT        NOT NULL,
    importance  FLOAT       DEFAULT 0.5,
    embedding   VECTOR(384),
    updated_at  TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (persona, memory_key)
);

-- ─── Mod metadata ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS mods_registry (
    id          SERIAL PRIMARY KEY,
    mod_name    TEXT        UNIQUE NOT NULL,
    mod_version TEXT        NOT NULL,
    enabled     BOOLEAN     DEFAULT TRUE,
    config      JSONB       DEFAULT '{}',
    loaded_at   TIMESTAMPTZ DEFAULT NOW()
);

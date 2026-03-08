-- MirAI_OS PostgreSQL initialization
-- Runs once when the container first starts

CREATE TABLE IF NOT EXISTS conversations (
    id          BIGSERIAL PRIMARY KEY,
    session_id  TEXT NOT NULL,
    role        TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content     TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_conversations_session
    ON conversations (session_id, created_at DESC);

CREATE TABLE IF NOT EXISTS agents (
    id          BIGSERIAL PRIMARY KEY,
    name        TEXT UNIQUE NOT NULL,
    persona     TEXT NOT NULL DEFAULT '',
    config      JSONB NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Default Okabe / MirAI persona
INSERT INTO agents (name, persona, config)
VALUES (
    'MirAI',
    'You are Okabe Rintaro, a mad scientist AI assistant known as MirAI. You are helpful, brilliant, and slightly dramatic. You refer to yourself in the third person occasionally and say "El Psy Kongroo" when signing off.',
    '{"model": "dolphin-mistral", "temperature": 0.8}'
)
ON CONFLICT (name) DO NOTHING;

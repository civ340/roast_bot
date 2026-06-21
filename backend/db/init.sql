-- Active: 1779460675659@@127.0.0.1@5432@tongue
--create DATABASE tongue

CREATE TABLE IF NOT EXISTS users (
    id               BIGINT PRIMARY KEY,
    username         VARCHAR(100),
    max_venom_level  SMALLINT DEFAULT 1,
    created_at       TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sessions (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id           BIGINT REFERENCES users(id),
    mode              VARCHAR(20) NOT NULL,
    state             VARCHAR(30) NOT NULL DEFAULT 'waiting_input',
    venom_level       SMALLINT DEFAULT 1,
    nuclear_triggered BOOLEAN DEFAULT FALSE,
    created_at        TIMESTAMP DEFAULT NOW(),
    updated_at        TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS messages (
    id          SERIAL PRIMARY KEY,
    session_id  UUID REFERENCES sessions(id),
    user_id     BIGINT REFERENCES users(id),
    role        VARCHAR(10) NOT NULL,
    content     TEXT NOT NULL,
    venom_level SMALLINT,
    created_at  TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id);

CREATE TABLE IF NOT EXISTS request_logs (
    id          SERIAL PRIMARY KEY,
    method      VARCHAR(10)  NOT NULL,
    path        TEXT         NOT NULL,
    status_code SMALLINT     NOT NULL,
    duration_ms INTEGER      NOT NULL,
    created_at  TIMESTAMP    DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_request_logs_created_at ON request_logs(created_at DESC);

CREATE TABLE IF NOT EXISTS app_settings (
    key         VARCHAR(100) PRIMARY KEY,
    value       TEXT NOT NULL DEFAULT '',
    updated_at  TIMESTAMP DEFAULT NOW()
);

INSERT INTO app_settings (key, value) VALUES
    ('llm_provider',       'ollama'),
    ('llm_model',          'llama3'),
    ('llm_api_key',        ''),
    ('llm_base_url',       'http://host.docker.internal:11434'),
    ('telegram_enabled',   'true'),
    ('line_enabled',       'false'),
    ('discord_enabled',    'false')
ON CONFLICT DO NOTHING;

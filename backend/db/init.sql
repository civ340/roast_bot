-- 這份檔案會在兩個時機執行：
--   1. postgres 容器第一次建立 volume 時（docker-entrypoint-initdb.d）
--   2. backend 每次啟動、以及 create_admin.py 執行時（app/db/database.py 的 run_migrations）
-- 所以每一句都必須可以重複執行。

-- users.id 的格式是「平台:平台上的用戶 ID」，例如 telegram:123456、line:Uabc...、discord:987654。
-- 三個平台的 ID 型別不同（LINE 是字串）而且數字 ID 可能相撞，所以不能直接拿平台 ID 當主鍵。
CREATE TABLE IF NOT EXISTS users (
    id               TEXT PRIMARY KEY,
    username         VARCHAR(100),
    max_venom_level  SMALLINT DEFAULT 1,
    created_at       TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sessions (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id           TEXT REFERENCES users(id),
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
    user_id     TEXT REFERENCES users(id),
    role        VARCHAR(10) NOT NULL,
    content     TEXT NOT NULL,
    venom_level SMALLINT,
    created_at  TIMESTAMP DEFAULT NOW()
);

-- 舊版 schema 的 users.id 是 BIGINT（直接存 Telegram user id）。
-- 偵測到舊型別時，把既有資料轉成 'telegram:<id>'，只會執行一次。
DO $$
BEGIN
    IF (
        SELECT data_type FROM information_schema.columns
        WHERE table_schema = current_schema() AND table_name = 'users' AND column_name = 'id'
    ) = 'bigint' THEN
        ALTER TABLE sessions DROP CONSTRAINT IF EXISTS sessions_user_id_fkey;
        ALTER TABLE messages DROP CONSTRAINT IF EXISTS messages_user_id_fkey;
        ALTER TABLE users    ALTER COLUMN id      TYPE TEXT USING 'telegram:' || id;
        ALTER TABLE sessions ALTER COLUMN user_id TYPE TEXT USING 'telegram:' || user_id;
        ALTER TABLE messages ALTER COLUMN user_id TYPE TEXT USING 'telegram:' || user_id;
        ALTER TABLE sessions ADD CONSTRAINT sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);
        ALTER TABLE messages ADD CONSTRAINT messages_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);
    END IF;
END $$;

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

CREATE TABLE IF NOT EXISTS admin_users (
    id            SERIAL PRIMARY KEY,
    username      VARCHAR(100) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at    TIMESTAMP DEFAULT NOW()
);

-- 後臺登入 session 存 DB（而非記憶體），backend 重啟或多副本部署不會讓使用者被登出。
-- token 欄位存的是 session token 的 SHA-256，不是 token 本身：資料庫外洩也拿不到可用的 cookie。
CREATE TABLE IF NOT EXISTS admin_sessions (
    token       TEXT PRIMARY KEY,
    username    VARCHAR(100) NOT NULL,
    expires_at  TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_admin_sessions_expires_at ON admin_sessions(expires_at);

-- llm_api_key 的 value 是加密過的（enc:v1: 開頭），金鑰由 API_SECRET_KEY 衍生
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

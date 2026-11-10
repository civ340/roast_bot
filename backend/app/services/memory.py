# 資料庫操作層：負責用戶、session、訊息的讀寫
# user_key 的格式是「平台:平台上的用戶 ID」（見 db/init.sql 的說明）
from uuid import UUID
import asyncpg


async def upsert_user(pool: asyncpg.Pool, user_key: str, username: str | None) -> None:
    # 用戶不存在則建立；已存在則更新顯示名稱（有帶才更新，LINE 拿不到名稱時不會把舊的蓋成空）
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO users (id, username) VALUES ($1, $2)
            ON CONFLICT (id) DO UPDATE SET username = COALESCE(EXCLUDED.username, users.username)
            """,
            user_key, username[:100] if username else None,
        )


async def create_session_with_exchange(
    pool: asyncpg.Pool,
    user_key: str,
    mode: str,          # 'roast' 或 'excuse'
    user_input: str,
    bot_output: str,
) -> UUID:
    # LLM 成功後才呼叫：一次寫入 session 與第一組問答，失敗就整組不留，不會有空的 session
    async with pool.acquire() as conn:
        async with conn.transaction():
            session_id = await conn.fetchval(
                """
                INSERT INTO sessions (user_id, mode, state, venom_level)
                VALUES ($1, $2, 'waiting_input', 1)
                RETURNING id
                """,
                user_key, mode,
            )
            await conn.executemany(
                """
                INSERT INTO messages (session_id, user_id, role, content, venom_level)
                VALUES ($1, $2, $3, $4, 1)
                """,
                [
                    (session_id, user_key, "user", user_input),
                    (session_id, user_key, "bot", bot_output),
                ],
            )
    return session_id


async def get_session(pool: asyncpg.Pool, session_id: UUID) -> dict | None:
    # 取得 session 的當前狀態
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT mode, venom_level, nuclear_triggered, user_id FROM sessions WHERE id = $1",
            session_id,
        )
        return dict(row) if row else None


async def last_exchange(pool: asyncpg.Pool, session_id: UUID) -> tuple[str | None, str | None]:
    # 回傳（用戶最後一次輸入, bot 最後一次回覆）。同一筆交易寫入的訊息 created_at 相同，所以用 id 當第二排序鍵
    async with pool.acquire() as conn:
        last_user_input = await conn.fetchval(
            "SELECT content FROM messages WHERE session_id = $1 AND role = 'user' "
            "ORDER BY created_at DESC, id DESC LIMIT 1",
            session_id,
        )
        last_bot_output = await conn.fetchval(
            "SELECT content FROM messages WHERE session_id = $1 AND role = 'bot' "
            "ORDER BY created_at DESC, id DESC LIMIT 1",
            session_id,
        )
    return last_user_input, last_bot_output


async def advance_session(
    pool: asyncpg.Pool,
    session_id: UUID,
    user_key: str,
    expected_level: int,
    new_level: int,
    is_nuclear: bool,
    bot_output: str,
    track_max_level: bool,
) -> bool:
    # LLM 成功後才呼叫：推進 session 等級並存下新回覆。
    # 用「等級還是我讀到的那個」當條件，同一個 session 被同時升級兩次時只有一個會成功，另一個回傳 False。
    async with pool.acquire() as conn:
        async with conn.transaction():
            updated = await conn.fetchval(
                """
                UPDATE sessions
                SET venom_level = $2, nuclear_triggered = $3, updated_at = NOW()
                WHERE id = $1 AND venom_level = $4 AND nuclear_triggered = FALSE
                RETURNING id
                """,
                session_id, new_level, is_nuclear, expected_level,
            )
            if not updated:
                return False
            await conn.execute(
                """
                INSERT INTO messages (session_id, user_id, role, content, venom_level)
                VALUES ($1, $2, 'bot', $3, $4)
                """,
                session_id, user_key, bot_output, new_level,
            )
            if track_max_level:
                await conn.execute(
                    "UPDATE users SET max_venom_level = GREATEST(max_venom_level, $1) WHERE id = $2",
                    new_level, user_key,
                )
    return True

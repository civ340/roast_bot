# 資料庫操作層：負責用戶、session、訊息的讀寫
import asyncpg
from uuid import UUID


async def get_or_create_user(pool: asyncpg.Pool, user_id: int, username: str | None) -> int:
    # 用戶不存在則建立，回傳該用戶的最高嗆辣等級
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT id, max_venom_level FROM users WHERE id = $1", user_id)
        if not row:
            await conn.execute(
                "INSERT INTO users (id, username) VALUES ($1, $2) ON CONFLICT DO NOTHING",
                user_id, username,
            )
            return 1
        return row["max_venom_level"]


async def create_session(pool: asyncpg.Pool, user_id: int, start_level: int, mode: str = "roast") -> str:
    # 建立新的對話 session，mode 為 'roast' 或 'excuse'
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO sessions (user_id, mode, state, venom_level)
            VALUES ($1, $2, 'waiting_input', $3)
            RETURNING id
            """,
            user_id, mode, start_level,
        )
        return str(row["id"])


async def save_message(
    pool: asyncpg.Pool,
    session_id: str,
    user_id: int,
    role: str,        # 'user' 或 'bot'
    content: str,
    venom_level: int,
):
    # 儲存一條訊息記錄
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO messages (session_id, user_id, role, content, venom_level)
            VALUES ($1, $2, $3, $4, $5)
            """,
            UUID(session_id), user_id, role, content, venom_level,
        )


async def escalate_venom(pool: asyncpg.Pool, session_id: str, user_id: int) -> int | None:
    # 嗆辣等級 +1（上限 5），同步更新用戶的歷史最高等級，回傳新等級（已達上限回傳 None）
    async with pool.acquire() as conn:
        new_level = await conn.fetchval(
            """
            UPDATE sessions
            SET venom_level = venom_level + 1, updated_at = NOW()
            WHERE id = $1 AND venom_level < 5
            RETURNING venom_level
            """,
            UUID(session_id),
        )
        if new_level:
            await conn.execute(
                "UPDATE users SET max_venom_level = GREATEST(max_venom_level, $1) WHERE id = $2",
                new_level, user_id,
            )
        return new_level


async def set_level(pool: asyncpg.Pool, session_id: str, level: int) -> None:
    # 直接設定 session 等級（借口模式用）
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE sessions SET venom_level = $1, updated_at = NOW() WHERE id = $2",
            level, UUID(session_id),
        )


async def trigger_nuclear(pool: asyncpg.Pool, session_id: str) -> None:
    # 標記此 session 已觸發核彈，防止繼續升級
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE sessions SET nuclear_triggered = TRUE WHERE id = $1",
            UUID(session_id),
        )


async def get_session(pool: asyncpg.Pool, session_id: str) -> dict | None:
    # 取得 session 的當前狀態
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT venom_level, nuclear_triggered, user_id FROM sessions WHERE id = $1",
            UUID(session_id),
        )
        return dict(row) if row else None

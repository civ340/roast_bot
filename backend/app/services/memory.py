import asyncpg
from uuid import UUID


async def get_or_create_user(pool: asyncpg.Pool, user_id: int, username: str | None) -> int:
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
    role: str,
    content: str,
    venom_level: int,
):
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO messages (session_id, user_id, role, content, venom_level)
            VALUES ($1, $2, $3, $4, $5)
            """,
            UUID(session_id), user_id, role, content, venom_level,
        )


async def escalate_venom(pool: asyncpg.Pool, session_id: str, user_id: int) -> int | None:
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
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE sessions SET venom_level = $1, updated_at = NOW() WHERE id = $2",
            level, UUID(session_id),
        )


async def trigger_nuclear(pool: asyncpg.Pool, session_id: str) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE sessions SET nuclear_triggered = TRUE WHERE id = $1",
            UUID(session_id),
        )


async def get_session(pool: asyncpg.Pool, session_id: str) -> dict | None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT venom_level, nuclear_triggered, user_id FROM sessions WHERE id = $1",
            UUID(session_id),
        )
        return dict(row) if row else None

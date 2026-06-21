# 後台統計路由：提供 Dashboard 所需的數據
from fastapi import APIRouter, Query
from uuid import UUID
from app.db.database import get_pool

router = APIRouter()


@router.get("/overview")
async def get_overview():
    # 回傳總覽數據：用戶數、場次、訊息數、核彈解鎖數、等級分布
    pool = await get_pool()
    async with pool.acquire() as conn:
        total_users    = await conn.fetchval("SELECT COUNT(*) FROM users")
        total_sessions = await conn.fetchval("SELECT COUNT(*) FROM sessions")
        total_messages = await conn.fetchval("SELECT COUNT(*) FROM messages WHERE role = 'user'")
        nuclear_count  = await conn.fetchval(
            "SELECT COUNT(*) FROM sessions WHERE nuclear_triggered = TRUE"
        )
        level_dist = await conn.fetch(
            "SELECT max_venom_level, COUNT(*) as count FROM users GROUP BY max_venom_level ORDER BY max_venom_level"
        )

    return {
        "total_users":              total_users,
        "total_sessions":           total_sessions,
        "total_messages":           total_messages,
        "nuclear_unlocked":         nuclear_count,
        "venom_level_distribution": [dict(r) for r in level_dist],
    }


@router.get("/sessions")
async def get_sessions(page: int = Query(1, ge=1), limit: int = Query(20, le=100)):
    # 分頁回傳所有對話 session 列表
    pool = await get_pool()
    offset = (page - 1) * limit
    async with pool.acquire() as conn:
        total = await conn.fetchval("SELECT COUNT(*) FROM sessions")
        rows = await conn.fetch(
            """
            SELECT s.id, s.user_id, u.username, s.mode, s.venom_level,
                   s.nuclear_triggered, s.created_at,
                   COUNT(m.id) AS message_count
            FROM sessions s
            LEFT JOIN users u ON u.id = s.user_id
            LEFT JOIN messages m ON m.session_id = s.id
            GROUP BY s.id, u.username
            ORDER BY s.created_at DESC
            LIMIT $1 OFFSET $2
            """,
            limit, offset,
        )
    return {
        "sessions": [dict(r) for r in rows],
        "total":    total,
    }


@router.get("/logs")
async def get_logs(
    page: int = Query(1, ge=1),
    limit: int = Query(50, le=200),
    status: str = Query("all"),  # all | success | error
):
    pool = await get_pool()
    offset = (page - 1) * limit
    where = ""
    if status == "success":
        where = "WHERE status_code < 400"
    elif status == "error":
        where = "WHERE status_code >= 400"
    async with pool.acquire() as conn:
        total = await conn.fetchval(f"SELECT COUNT(*) FROM request_logs {where}")
        rows = await conn.fetch(
            f"""
            SELECT id, method, path, status_code, duration_ms, created_at
            FROM request_logs {where}
            ORDER BY created_at DESC
            LIMIT $1 OFFSET $2
            """,
            limit, offset,
        )
    return {"logs": [dict(r) for r in rows], "total": total}


@router.get("/sessions/{session_id}/messages")
async def get_messages(session_id: str):
    # 回傳指定 session 的完整訊息記錄
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, session_id, user_id, role, content, venom_level, created_at
            FROM messages
            WHERE session_id = $1
            ORDER BY created_at ASC
            """,
            UUID(session_id),
        )
    return [dict(r) for r in rows]

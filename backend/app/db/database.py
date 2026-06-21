# PostgreSQL 連線池管理，整個應用程式共用同一個 pool
import asyncpg
from app.config import settings

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    # 第一次呼叫時建立 pool，之後直接回傳已建立的
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(settings.database_url, min_size=2, max_size=10)
    return _pool


async def close_pool():
    # 應用程式關閉時釋放所有連線
    global _pool
    if _pool:
        await _pool.close()
        _pool = None

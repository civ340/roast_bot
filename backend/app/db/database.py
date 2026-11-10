# PostgreSQL 連線池管理，整個應用程式共用同一個 pool
from pathlib import Path
import asyncpg
from app.config import settings

INIT_SQL_PATH = Path(__file__).resolve().parents[2] / "db" / "init.sql"

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


async def run_migrations(pool: asyncpg.Pool) -> None:
    # 既有資料庫的 volume 不會重跑 init.sql，所以 backend 每次啟動都重放一次。
    # init.sql 全部語句都可重複執行（IF NOT EXISTS / ON CONFLICT DO NOTHING / 有條件的 DO 區塊），
    # 新舊資料庫跑完都會收斂到同一份 schema。
    async with pool.acquire() as conn:
        await conn.execute(INIT_SQL_PATH.read_text(encoding="utf-8"))

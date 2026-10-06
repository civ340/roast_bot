# CLI 工具：手動建立/重設後臺管理員帳號
import asyncio
import getpass
import sys
from pathlib import Path

from app.db.database import get_pool, close_pool
from app.services import auth

INIT_SQL_PATH = Path(__file__).resolve().parent / "db" / "init.sql"


async def main():
    username = input("帳號: ").strip()
    if not username:
        print("帳號不可為空")
        sys.exit(1)

    password = getpass.getpass("密碼: ")
    confirm = getpass.getpass("再次輸入密碼: ")
    if password != confirm:
        print("兩次輸入的密碼不一致")
        sys.exit(1)
    if len(password) < 8:
        print("密碼至少需要 8 個字元")
        sys.exit(1)

    password_hash = auth.hash_password(password)

    pool = await get_pool()
    async with pool.acquire() as conn:
        # 既有資料庫的 volume 不會重跑 init.sql，這裡重放整份 init.sql 確保表存在，
        # 全部語句都是 IF NOT EXISTS / ON CONFLICT DO NOTHING，重跑安全，
        # 且不用在這裡另外手刻一份會跟 init.sql 走鐘的 schema
        await conn.execute(INIT_SQL_PATH.read_text(encoding="utf-8"))
        await conn.execute(
            """
            INSERT INTO admin_users (username, password_hash)
            VALUES ($1, $2)
            ON CONFLICT (username) DO UPDATE SET password_hash = EXCLUDED.password_hash
            """,
            username, password_hash,
        )
    await close_pool()
    print(f"帳號「{username}」已建立/更新。")


if __name__ == "__main__":
    asyncio.run(main())

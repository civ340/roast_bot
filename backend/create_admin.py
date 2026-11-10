# CLI 工具：手動建立/重設後臺管理員帳號
import asyncio
import getpass
import sys

from app.db.database import get_pool, close_pool, run_migrations
from app.services import auth


async def main():
    username = input("帳號: ").strip()
    if not username:
        print("帳號不可為空")
        sys.exit(1)
    if len(username) > 100:
        print("帳號最多 100 個字元")
        sys.exit(1)

    password = getpass.getpass("密碼: ")
    confirm = getpass.getpass("再次輸入密碼: ")
    if password != confirm:
        print("兩次輸入的密碼不一致")
        sys.exit(1)
    if len(password) < 8:
        print("密碼至少需要 8 個字元")
        sys.exit(1)
    # bcrypt 只會用到前 72 bytes，超過的部分會被默默忽略，直接擋掉比較不會誤會
    if len(password.encode()) > 72:
        print("密碼最多 72 bytes")
        sys.exit(1)

    password_hash = auth.hash_password(password)

    pool = await get_pool()
    # 既有資料庫的 volume 不會重跑 init.sql，這裡重放一次確保表存在（重跑安全，見 run_migrations）
    await run_migrations(pool)
    async with pool.acquire() as conn:
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

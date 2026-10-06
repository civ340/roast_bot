# 後臺登入驗證：密碼雜湊比對 + DB 儲存的 session 管理（存 DB 而非記憶體，backend 重啟或多副本部署不會讓使用者被登出）
from __future__ import annotations
import asyncio
import secrets
import time
from datetime import datetime, timedelta, timezone
import bcrypt
import asyncpg

SESSION_COOKIE = "session"
SESSION_TTL_SECONDS = 7 * 24 * 60 * 60  # 7 天

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_WINDOW_SECONDS = 15 * 60  # 15 分鐘內失敗滿 5 次就鎖住該帳號
MAX_TRACKED_USERNAMES = 10_000  # 避免用不存在的帳號洗爆這個 dict

# username -> 失敗嘗試的時間戳記列表（僅記憶體，重啟後歸零，可接受）
_failed_attempts: dict[str, list[float]] = {}
# 全域鎖：admin 登入本來就是低流量端點，直接整段序列化最簡單也最不會漏算失敗次數
_auth_lock = asyncio.Lock()

SESSION_CACHE_TTL_SECONDS = 30

# token -> (username, cached_at)：短 TTL 快取，減少每個 request 都查一次 DB；
# logout 會馬上清掉對應快取，登出立即生效，不用等 TTL 過期
_session_cache: dict[str, tuple[str, float]] = {}


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


async def authenticate(pool: asyncpg.Pool, username: str, password: str) -> bool:
    async with _auth_lock:
        now = time.time()

        if len(_failed_attempts) > MAX_TRACKED_USERNAMES:
            stale = [u for u, ts in _failed_attempts.items() if not ts or now - ts[-1] >= LOCKOUT_WINDOW_SECONDS]
            for u in stale:
                _failed_attempts.pop(u, None)

        attempts = _failed_attempts.setdefault(username, [])
        attempts[:] = [t for t in attempts if now - t < LOCKOUT_WINDOW_SECONDS]
        if len(attempts) >= MAX_FAILED_ATTEMPTS:
            return False

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT password_hash FROM admin_users WHERE username = $1", username,
            )
        # bcrypt 是同步、吃 CPU 的呼叫，丟到 thread 執行才不會佔住 event loop
        # （否則會卡住其他 request，包括 bot 打進來的 /api/roast、/api/excuse）
        if row:
            ok = await asyncio.to_thread(verify_password, password, row["password_hash"])
        else:
            ok = False
        if ok:
            _failed_attempts.pop(username, None)
        else:
            attempts.append(time.time())
        return ok


async def create_session(pool: asyncpg.Pool, username: str) -> str:
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=SESSION_TTL_SECONDS)
    async with pool.acquire() as conn:
        # 沒有排程清理過期 session 的機制，順手在每次登入時清掉，避免這張表無限長大
        await conn.execute("DELETE FROM admin_sessions WHERE expires_at <= NOW()")
        await conn.execute(
            "INSERT INTO admin_sessions (token, username, expires_at) VALUES ($1, $2, $3)",
            token, username, expires_at,
        )
    return token


async def get_session_username(pool: asyncpg.Pool, token: str | None) -> str | None:
    if not token:
        return None

    now = time.time()
    cached = _session_cache.get(token)
    if cached and now - cached[1] < SESSION_CACHE_TTL_SECONDS:
        return cached[0]

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT username FROM admin_sessions WHERE token = $1 AND expires_at > NOW()", token,
        )
    if not row:
        _session_cache.pop(token, None)
        return None

    _session_cache[token] = (row["username"], now)
    return row["username"]


async def revoke_session(pool: asyncpg.Pool, token: str | None) -> None:
    if not token:
        return
    _session_cache.pop(token, None)
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM admin_sessions WHERE token = $1", token)

# 後臺登入驗證：密碼雜湊比對 + DB 儲存的 session 管理（存 DB 而非記憶體，backend 重啟或多副本部署不會讓使用者被登出）
from __future__ import annotations
import asyncio
import hashlib
import secrets
import time
from datetime import datetime, timedelta, timezone
import bcrypt
import asyncpg

SESSION_COOKIE = "session"
SESSION_TTL_SECONDS = 7 * 24 * 60 * 60  # 7 天

LOCKOUT_WINDOW_SECONDS = 15 * 60
# 15 分鐘內的登入失敗次數上限，分三層：
#   user+ip：同一個來源猜同一個帳號，5 次就擋（擋一般的暴力破解）
#   ip     ：同一個來源不管猜哪個帳號，20 次就擋（擋換帳號名亂槍打鳥）
#   user   ：同一個帳號被所有來源加起來猜 50 次才整個鎖住（擋分散式暴力破解）。
#            門檻刻意拉高：如果只看帳號、5 次就鎖，任何知道帳號名的人都能把管理員永久鎖在門外。
_FAILURE_LIMITS = {"user_ip": 5, "ip": 20, "user": 50}
MAX_TRACKED_KEYS = 10_000  # 避免用不存在的帳號 / 偽造的來源洗爆這個 dict

# key -> 失敗嘗試的時間戳記列表（僅記憶體，重啟後歸零，可接受）
_failures: dict[str, list[float]] = {}
# 全域鎖：admin 登入本來就是低流量端點，直接整段序列化最簡單也最不會漏算失敗次數
_auth_lock = asyncio.Lock()

SESSION_CACHE_TTL_SECONDS = 30

# token 雜湊 -> (username, cached_at)：短 TTL 快取，減少每個 request 都查一次 DB；
# logout 會馬上清掉對應快取，登出立即生效，不用等 TTL 過期
_session_cache: dict[str, tuple[str, float]] = {}

# 帳號不存在時也跑一次 bcrypt，回應時間才不會洩漏「這個帳號存不存在」
_dummy_hash: str | None = None


class TooManyAttempts(Exception):
    pass


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def _get_dummy_hash() -> str:
    global _dummy_hash
    if _dummy_hash is None:
        _dummy_hash = hash_password(secrets.token_urlsafe(16))
    return _dummy_hash


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _recent_failures(key: str, now: float) -> int:
    attempts = _failures.get(key)
    if not attempts:
        return 0
    attempts[:] = [t for t in attempts if now - t < LOCKOUT_WINDOW_SECONDS]
    if not attempts:
        _failures.pop(key, None)
    return len(attempts)


async def authenticate(pool: asyncpg.Pool, username: str, password: str, client_ip: str) -> bool:
    # 回傳帳密是否正確；失敗次數超過上限時丟 TooManyAttempts
    async with _auth_lock:
        now = time.time()

        if len(_failures) > MAX_TRACKED_KEYS:
            for key in list(_failures):
                _recent_failures(key, now)

        keys = {
            "user_ip": f"user_ip:{username}|{client_ip}",
            "ip":      f"ip:{client_ip}",
            "user":    f"user:{username}",
        }
        for kind, key in keys.items():
            if _recent_failures(key, now) >= _FAILURE_LIMITS[kind]:
                raise TooManyAttempts()

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT password_hash FROM admin_users WHERE username = $1", username,
            )
        # bcrypt 是同步、吃 CPU 的呼叫，丟到 thread 執行才不會佔住 event loop
        # （否則會卡住其他 request，包括 bot 打進來的 /api/roast、/api/excuse）
        password_hash = row["password_hash"] if row else _get_dummy_hash()
        matched = await asyncio.to_thread(verify_password, password, password_hash)
        ok = bool(row) and matched

        if ok:
            _failures.pop(keys["user_ip"], None)
            _failures.pop(keys["user"], None)
        else:
            failed_at = time.time()
            for key in keys.values():
                _failures.setdefault(key, []).append(failed_at)
        return ok


async def create_session(pool: asyncpg.Pool, username: str) -> str:
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=SESSION_TTL_SECONDS)
    async with pool.acquire() as conn:
        # 順手在每次登入時清掉過期 session（main.py 另有每小時的排程清理）
        await conn.execute("DELETE FROM admin_sessions WHERE expires_at <= NOW()")
        await conn.execute(
            "INSERT INTO admin_sessions (token, username, expires_at) VALUES ($1, $2, $3)",
            _hash_token(token), username, expires_at,
        )
    return token


async def get_session_username(pool: asyncpg.Pool, token: str | None) -> str | None:
    if not token:
        return None
    token_hash = _hash_token(token)

    now = time.time()
    cached = _session_cache.get(token_hash)
    if cached and now - cached[1] < SESSION_CACHE_TTL_SECONDS:
        return cached[0]

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT username FROM admin_sessions WHERE token = $1 AND expires_at > NOW()", token_hash,
        )
    if not row:
        _session_cache.pop(token_hash, None)
        return None

    _session_cache[token_hash] = (row["username"], now)
    return row["username"]


async def revoke_session(pool: asyncpg.Pool, token: str | None) -> None:
    if not token:
        return
    token_hash = _hash_token(token)
    _session_cache.pop(token_hash, None)
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM admin_sessions WHERE token = $1", token_hash)

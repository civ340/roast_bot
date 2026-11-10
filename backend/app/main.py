# FastAPI 應用程式入口：路由註冊、啟動設定載入、認證與請求紀錄
import asyncio
import logging
import secrets
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.background import BackgroundTask
from starlette.middleware.base import BaseHTTPMiddleware
from app.config import settings as env, check_api_secret_key
from app.db.database import get_pool, close_pool, run_migrations
from app.errors import AppError
from app.services import app_settings as cfg
from app.services import auth
from app.routers import roast, excuse, stats, settings, line, auth as auth_router

logger = logging.getLogger(__name__)

# 不需要登入就能存取的路徑：/api/auth 與 /webhook 供登入與平台 webhook 使用。
# /api/roast、/api/excuse 是 Telegram/Discord bot 對 backend 的內部呼叫，不是後台管理介面，
# 不能對外公開，改用共享密鑰（X-Internal-Secret）驗證。nginx 那層也會直接擋掉這兩個路徑。
PUBLIC_PATHS = {"/health"}
PUBLIC_PREFIXES = ("/api/auth/", "/webhook/")
INTERNAL_PREFIXES = ("/api/roast/", "/api/excuse/")
INTERNAL_SECRET_HEADER = "X-Internal-Secret"

CLEANUP_INTERVAL_SECONDS = 60 * 60


async def _cleanup_once():
    # 清掉過期資料，避免資料表無限長大
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM admin_sessions WHERE expires_at <= NOW()")
        if env.log_retention_days > 0:
            await conn.execute(
                "DELETE FROM request_logs WHERE created_at < NOW() - make_interval(days => $1)",
                env.log_retention_days,
            )
        if env.message_retention_days > 0:
            async with conn.transaction():
                await conn.execute(
                    "DELETE FROM messages WHERE created_at < NOW() - make_interval(days => $1)",
                    env.message_retention_days,
                )
                await conn.execute(
                    """
                    DELETE FROM sessions s
                    WHERE s.created_at < NOW() - make_interval(days => $1)
                      AND NOT EXISTS (SELECT 1 FROM messages m WHERE m.session_id = s.id)
                    """,
                    env.message_retention_days,
                )


async def _cleanup_loop():
    while True:
        try:
            await _cleanup_once()
        except Exception:
            logger.exception("定期清理失敗")
        await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    check_api_secret_key()

    # 啟動時建立 DB pool、確保 schema 是最新的，並載入後台設定到記憶體
    pool = await get_pool()
    await run_migrations(pool)
    await cfg.load(pool)
    await cfg.encrypt_legacy_secrets(pool)
    cleanup_task = asyncio.create_task(_cleanup_loop())
    yield
    # 關閉時釋放 DB 連線
    cleanup_task.cancel()
    await close_pool()


app = FastAPI(lifespan=lifespan)


@app.exception_handler(AppError)
async def _app_error_handler(request: Request, exc: AppError):
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)


async def _log_request(method: str, path: str, status_code: int, duration_ms: int):
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO request_logs (method, path, status_code, duration_ms) VALUES ($1, $2, $3, $4)",
                method, path, status_code, duration_ms,
            )
    except Exception:
        logger.exception("Failed to write request log for %s %s", method, path)


class RequestLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.monotonic()
        response = await call_next(request)
        duration_ms = int((time.monotonic() - start) * 1000)
        if request.url.path != "/health":
            log_task = BackgroundTask(
                # path 是 client 給的，截斷後再存，免得有人用超長網址灌爆 request_logs
                _log_request, request.method, request.url.path[:500], response.status_code, duration_ms,
            )
            if response.background is not None:
                response.background = _chain_background(response.background, log_task)
            else:
                response.background = log_task
        return response


def _chain_background(first: BackgroundTask, second: BackgroundTask) -> BackgroundTask:
    async def run():
        try:
            await first()
        except Exception:
            logger.exception("Background task failed before request log write")
        await second()
    return BackgroundTask(run)


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if (
            request.method == "OPTIONS"
            or path in PUBLIC_PATHS
            or path.startswith(PUBLIC_PREFIXES)
            or not path.startswith("/api/")
        ):
            return await call_next(request)

        if path.startswith(INTERNAL_PREFIXES):
            header_secret = request.headers.get(INTERNAL_SECRET_HEADER, "")
            # 比對 bytes：compare_digest 遇到非 ASCII 的 str 會丟例外
            if env.api_secret_key and secrets.compare_digest(
                header_secret.encode(), env.api_secret_key.encode(),
            ):
                return await call_next(request)
            return JSONResponse({"detail": "Unauthorized"}, status_code=401)

        pool = await get_pool()
        username = await auth.get_session_username(pool, request.cookies.get(auth.SESSION_COOKIE))
        if not username:
            return JSONResponse({"detail": "Unauthorized"}, status_code=401)

        return await call_next(request)


app.add_middleware(AuthMiddleware)
app.add_middleware(RequestLogMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in env.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router, prefix="/api/auth")
app.include_router(roast.router,    prefix="/api/roast")
app.include_router(excuse.router,   prefix="/api/excuse")
app.include_router(stats.router,    prefix="/api/stats")
app.include_router(settings.router, prefix="/api/settings")
app.include_router(line.router,     prefix="/webhook")


@app.get("/health")
async def health():
    return {"status": "ok"}

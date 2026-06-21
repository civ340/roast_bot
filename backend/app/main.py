# FastAPI 應用程式入口：路由註冊、啟動設定載入、LINE webhook
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from app.db.database import get_pool, close_pool
from app.services import app_settings as cfg
from app.routers import roast, excuse, stats, settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 啟動時建立 DB pool 並載入後台設定到記憶體
    pool = await get_pool()
    await cfg.load(pool)
    yield
    # 關閉時釋放 DB 連線
    await close_pool()


app = FastAPI(lifespan=lifespan)


class RequestLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.monotonic()
        response = await call_next(request)
        duration_ms = int((time.monotonic() - start) * 1000)
        if request.url.path != "/health":
            try:
                pool = await get_pool()
                async with pool.acquire() as conn:
                    await conn.execute(
                        "INSERT INTO request_logs (method, path, status_code, duration_ms) VALUES ($1, $2, $3, $4)",
                        request.method, request.url.path, response.status_code, duration_ms,
                    )
            except Exception:
                pass
        return response


app.add_middleware(RequestLogMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(roast.router,    prefix="/api/roast")
app.include_router(excuse.router,   prefix="/api/excuse")
app.include_router(stats.router,    prefix="/api/stats")
app.include_router(settings.router, prefix="/api/settings")


@app.get("/health")
async def health():
    return {"status": "ok"}


# ── LINE Webhook ───────────────────────────────────────────────────────────────

@app.post("/webhook/line")
async def line_webhook(request: Request):
    # 接收 LINE 平台的訊息推送，驗證簽名後處理文字訊息
    if not cfg.is_enabled("line_enabled"):
        raise HTTPException(status_code=403, detail="LINE not enabled")

    from app.config import settings as env
    if not env.line_channel_secret or not env.line_channel_access_token:
        raise HTTPException(status_code=500, detail="LINE tokens not configured")

    from linebot.v3 import WebhookParser
    from linebot.v3.exceptions import InvalidSignatureError
    from linebot.v3.webhooks import MessageEvent, TextMessageContent
    from linebot.v3.messaging import (
        AsyncApiClient, AsyncMessagingApi, Configuration,
        ReplyMessageRequest, TextMessage, QuickReply, QuickReplyItem, MessageAction,
    )
    from app.services import llm

    signature = request.headers.get("X-Line-Signature", "")
    body = await request.body()

    parser = WebhookParser(env.line_channel_secret)
    try:
        events = parser.parse(body.decode(), signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    config = Configuration(access_token=env.line_channel_access_token)
    async with AsyncApiClient(config) as api_client:
        line_api = AsyncMessagingApi(api_client)

        for event in events:
            if not isinstance(event, MessageEvent):
                continue
            if not isinstance(event.message, TextMessageContent):
                continue

            text = event.message.text.strip()
            reply_token = event.reply_token

            # 「藉口」開頭 → 借口模式，其餘 → 嗆辣模式
            if text.startswith("藉口"):
                situation = text[2:].strip() or text
                result_text = await llm.generate_excuse(situation, excuse_level=1)
                quick_reply = QuickReply(items=[
                    QuickReplyItem(action=MessageAction(label="再誇一點 🎭", text=f"__excuse_more__{situation}")),
                    QuickReplyItem(action=MessageAction(label="換個情況 🔄", text="換個情況")),
                ])
                reply = TextMessage(text=f"📋 {result_text}", quick_reply=quick_reply)
            else:
                result_text = await llm.generate_roast(text, venom_level=1)
                quick_reply = QuickReply(items=[
                    QuickReplyItem(action=MessageAction(label="再毒一點 🐍", text=f"__roast_more__{text}")),
                    QuickReplyItem(action=MessageAction(label="換個目標 🎯", text="換個目標")),
                ])
                reply = TextMessage(text=f"😏 {result_text}", quick_reply=quick_reply)

            await line_api.reply_message(ReplyMessageRequest(
                reply_token=reply_token,
                messages=[reply],
            ))

    return {"status": "ok"}

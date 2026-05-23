from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.db.database import get_pool, close_pool
from app.services import app_settings as cfg
from app.routers import roast, excuse, stats, settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    pool = await get_pool()
    await cfg.load(pool)
    yield
    await close_pool()


app = FastAPI(lifespan=lifespan)

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


# ── LINE webhook ───────────────────────────────────────────────────────────────

@app.post("/webhook/line")
async def line_webhook(request: Request):
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

            if text.startswith("借口"):
                situation = text[2:].strip() or text
                result_text = await llm.generate_excuse(situation, excuse_level=1)
                quick_reply = QuickReply(items=[
                    QuickReplyItem(action=MessageAction(label="再誇一點 🎭", text=f"__excuse_more__{situation}")),
                    QuickReplyItem(action=MessageAction(label="換個情況 🔄", text="換個情況")),
                ])
                reply = TextMessage(text=f"📋 {result_text}", quick_reply=quick_reply)
            else:
                content = text
                result_text = await llm.generate_roast(content, venom_level=1)
                quick_reply = QuickReply(items=[
                    QuickReplyItem(action=MessageAction(label="再毒一點 🐍", text=f"__roast_more__{content}")),
                    QuickReplyItem(action=MessageAction(label="換個目標 🎯", text="換個目標")),
                ])
                reply = TextMessage(text=f"😏 {result_text}", quick_reply=quick_reply)

            await line_api.reply_message(ReplyMessageRequest(
                reply_token=reply_token,
                messages=[reply],
            ))

    return {"status": "ok"}

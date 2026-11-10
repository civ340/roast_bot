# LINE webhook：驗證簽名後在背景處理事件，用 reply token 回覆
import asyncio
import logging
from uuid import UUID
from fastapi import APIRouter, HTTPException, Request
from linebot.v3 import WebhookParser
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    AsyncApiClient, AsyncMessagingApi, Configuration,
    PostbackAction, QuickReply, QuickReplyItem, ReplyMessageRequest, TextMessage,
)
from linebot.v3.webhooks import MessageEvent, PostbackEvent, TextMessageContent
from app import emoji
from app.config import settings as env, MAX_INPUT_CHARS
from app.db.database import get_pool
from app.errors import AlreadyMaxed, EscalationConflict, NotYourSession, RateLimited, SessionNotFound
from app.services import app_settings as cfg
from app.services import conversation

logger = logging.getLogger(__name__)
router = APIRouter()

HELP_TEXT = "直接傳文字給我 → 我嗆你。\n以「藉口」開頭（例：藉口我遲到了）→ 我幫你想藉口。"

ESCALATE_LABEL = {"roast": "再毒一點 🐍", "excuse": "再誇一點 🎭"}
RESET_LABEL = {"roast": "換個目標 🎯", "excuse": "換個情況 🔄"}

# 背景任務要留一份參考，否則可能在執行到一半時被垃圾回收
_tasks: set[asyncio.Task] = set()


@router.post("/line")
async def line_webhook(request: Request):
    if not cfg.is_enabled("line_enabled"):
        raise HTTPException(status_code=403, detail="LINE not enabled")
    if not env.line_channel_secret or not env.line_channel_access_token:
        raise HTTPException(status_code=500, detail="LINE tokens not configured")

    signature = request.headers.get("X-Line-Signature", "")
    body = await request.body()

    parser = WebhookParser(env.line_channel_secret)
    try:
        events = parser.parse(body.decode(), signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    except ValueError:  # 包含 UnicodeDecodeError、JSON 格式錯誤
        raise HTTPException(status_code=400, detail="Invalid body")

    # LLM 可能要跑幾十秒，先回 200 給 LINE 再慢慢處理，
    # 不然 LINE 會判定 webhook 逾時（還可能重送同一批事件，變成重複回覆）
    task = asyncio.create_task(_handle_events(events))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)

    return {"status": "ok"}


async def _handle_events(events: list) -> None:
    config = Configuration(access_token=env.line_channel_access_token)
    async with AsyncApiClient(config) as api_client:
        line_api = AsyncMessagingApi(api_client)
        for event in events:
            try:
                reply = await _build_reply(event)
                if reply is not None:
                    await line_api.reply_message(ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[reply],
                    ))
            except Exception:
                logger.exception("處理 LINE 事件失敗")


async def _build_reply(event) -> TextMessage | None:
    # 依事件內容決定要做什麼，回傳要回覆的訊息；不需要回覆時回傳 None
    line_user_id = getattr(event.source, "user_id", None) if event.source else None
    if not line_user_id:
        return None
    user_key = conversation.make_user_key("line", line_user_id)
    pool = await get_pool()

    if isinstance(event, MessageEvent) and isinstance(event.message, TextMessageContent):
        text = event.message.text.strip()
        # 「藉口」開頭 → 借口模式，其餘 → 嗆辣模式
        if text.startswith("藉口"):
            mode = "excuse"
            text = text[2:].strip() or text
        else:
            mode = "roast"
        if not text:
            return None
        if len(text) > MAX_INPUT_CHARS:
            return TextMessage(text=f"太長了，最多 {MAX_INPUT_CHARS} 字。")
        action = conversation.start(pool, mode, user_key, None, text)

    elif isinstance(event, PostbackEvent):
        # Quick Reply 按鈕帶回來的資料：'reset' 或 'esc:<mode>:<session_id>'
        data = event.postback.data or ""
        if data == "reset":
            return TextMessage(text=HELP_TEXT)
        parts = data.split(":")
        if len(parts) != 3 or parts[0] != "esc" or parts[1] not in ESCALATE_LABEL:
            return None
        mode = parts[1]
        try:
            session_id = UUID(parts[2])
        except ValueError:
            return None
        action = conversation.escalate(pool, mode, user_key, session_id)

    else:
        return None

    try:
        result = await action
    except RateLimited:
        return TextMessage(text="慢一點，你傳太快了。等一下再來。")
    except NotYourSession:
        return TextMessage(text="這不是你的對話。")
    except EscalationConflict:
        return TextMessage(text="上一個還在處理，等一下。")
    except (SessionNotFound, AlreadyMaxed):
        return TextMessage(text="這場對話已經結束了，直接傳新的文字給我吧。")
    except Exception:
        logger.exception("LINE 對話處理失敗")
        return TextMessage(text="出了點問題，稍後再試。")

    return _format_reply(mode, result)


def _format_reply(mode: str, result: conversation.Reply) -> TextMessage:
    # 按鈕用 postback 而不是「幫用戶送出一則文字」：
    # 升級需要知道是哪一場對話（session_id），而且送出的文字會被當成新訊息再嗆一次
    items = []
    if result.can_escalate:
        items.append(QuickReplyItem(action=PostbackAction(
            label=ESCALATE_LABEL[mode],
            data=f"esc:{mode}:{result.session_id}",
            display_text=ESCALATE_LABEL[mode],
        )))
    items.append(QuickReplyItem(action=PostbackAction(
        label=RESET_LABEL[mode],
        data="reset",
        display_text=RESET_LABEL[mode],
    )))
    prefix = emoji.for_reply(mode, result.level, result.is_nuclear)
    return TextMessage(text=f"{prefix} {result.text}", quick_reply=QuickReply(items=items))

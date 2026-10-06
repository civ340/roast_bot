# Telegram Bot：處理用戶訊息、模式選擇（嗆辣/借口）、升級按鈕互動
import logging
import secrets
import time
import httpx
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from app.config import settings

API_BASE = f"{settings.api_base_url}/api"
INTERNAL_HEADERS = {"X-Internal-Secret": settings.api_secret_key}

ROAST_EMOJI = ["😏", "😈", "🐍", "☠️", "👑"]
EXCUSE_EMOJI = ["📋", "🎭", "💣", "🌀", "🚀", "👑"]

# 設定快取秒數：bot 為獨立行程，需定期從 DB 重新載入才能反映後台的開關變更
SETTINGS_TTL = 15
_settings_loaded_at = 0.0

# 每位用戶最多保留幾筆可重試的動作
MAX_RETRY_ACTIONS = 20

logger = logging.getLogger(__name__)

MAIN_MENU = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("嗆我 🐍", callback_data="mode:roast"),
        InlineKeyboardButton("幫我找借口 📋", callback_data="mode:excuse"),
    ]
])


def _main_menu_markup():
    return MAIN_MENU


def _retry_markup(context, action):
    # 以短 id 保存這次失敗的動作，按鈕只帶 id，避免舊按鈕重跑到最新的動作
    actions = context.user_data.setdefault("retry_actions", {})
    retry_id = secrets.token_hex(4)
    actions[retry_id] = action
    while len(actions) > MAX_RETRY_ACTIONS:
        actions.pop(next(iter(actions)))
    return InlineKeyboardMarkup([[InlineKeyboardButton("重試 🔄", callback_data=f"retry:{retry_id}")]])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_enabled(update, context):
        return
    context.user_data.clear()
    await update.message.reply_text("你好，想幹嘛？", reply_markup=_main_menu_markup())


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_enabled(update, context):
        return

    mode = context.user_data.get("mode")

    if not mode:
        await update.message.reply_text("先選一個。", reply_markup=_main_menu_markup())
        return

    user = update.effective_user
    text = update.message.text

    if mode == "roast":
        await _do_roast(update, context, user.id, user.username, text)
    else:
        await _do_excuse(update, context, user.id, user.username, text)


async def _do_roast(update, context, user_id, username, text):
    action = {"type": "roast", "user_id": user_id, "username": username, "text": text}
    await context.bot.send_chat_action(update.effective_chat.id, "typing")
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(f"{API_BASE}/roast/start", json={
                "content": text,
                "user_id": user_id,
                "username": username,
            }, headers=INTERNAL_HEADERS)
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        await update.effective_message.reply_text("出了點問題，稍後再試。", reply_markup=_retry_markup(context, action))
        return

    emoji = ROAST_EMOJI[data["venom_level"] - 1]
    keyboard = []
    if data["can_escalate"]:
        keyboard.append([InlineKeyboardButton(
            "再毒一點 🐍",
            callback_data=f"roast_esc:{data['session_id']}:{user_id}",
        )])
    keyboard.append([InlineKeyboardButton("換個目標 🎯", callback_data="reset")])

    await update.effective_message.reply_text(
        f"{emoji} {data['roast']}",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def _do_excuse(update, context, user_id, username, text):
    action = {"type": "excuse", "user_id": user_id, "username": username, "text": text}
    await context.bot.send_chat_action(update.effective_chat.id, "typing")
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(f"{API_BASE}/excuse/start", json={
                "situation": text,
                "user_id": user_id,
                "username": username,
            }, headers=INTERNAL_HEADERS)
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        await update.effective_message.reply_text("出了點問題，稍後再試。", reply_markup=_retry_markup(context, action))
        return

    emoji = EXCUSE_EMOJI[data["excuse_level"] - 1]
    keyboard = [
        [InlineKeyboardButton("再誇一點 🎭", callback_data=f"excuse_esc:{data['session_id']}:{user_id}")],
        [InlineKeyboardButton("換個情況 🔄", callback_data="excuse_new")],
    ]

    await update.effective_message.reply_text(
        f"{emoji} {data['excuse']}",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def _do_roast_escalate(update, context, session_id, user_id):
    # 失敗時在原訊息上改為重試按鈕，重試時 callback 的 message 即為原本那則訊息
    query = update.callback_query
    action = {"type": "roast_esc", "session_id": session_id, "user_id": user_id}
    await context.bot.send_chat_action(update.effective_chat.id, "typing")
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(f"{API_BASE}/roast/escalate", json={
                "session_id": session_id,
                "user_id": int(user_id),
            }, headers=INTERNAL_HEADERS)
            resp.raise_for_status()
            result = resp.json()
    except Exception:
        await query.edit_message_text("出了點問題，稍後再試。", reply_markup=_retry_markup(context, action))
        return

    if result["is_nuclear"]:
        msg = f"💥 {result['roast']}"
        keyboard = [[InlineKeyboardButton("換個目標 🎯", callback_data="reset")]]
    else:
        emoji = ROAST_EMOJI[result["venom_level"] - 1]
        msg = f"{emoji} {result['roast']}"
        keyboard = [
            [InlineKeyboardButton("再毒一點 🐍", callback_data=f"roast_esc:{session_id}:{user_id}")],
            [InlineKeyboardButton("換個目標 🎯", callback_data="reset")],
        ]

    await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))


async def _do_excuse_escalate(update, context, session_id, user_id):
    query = update.callback_query
    action = {"type": "excuse_esc", "session_id": session_id, "user_id": user_id}
    await context.bot.send_chat_action(update.effective_chat.id, "typing")
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(f"{API_BASE}/excuse/escalate", json={
                "session_id": session_id,
                "user_id": int(user_id),
            }, headers=INTERNAL_HEADERS)
            resp.raise_for_status()
            result = resp.json()
    except Exception:
        await query.edit_message_text("出了點問題，稍後再試。", reply_markup=_retry_markup(context, action))
        return

    if result["is_nuclear"]:
        msg = f"💣 {result['excuse']}"
        keyboard = [[InlineKeyboardButton("換個情況 🔄", callback_data="excuse_new")]]
    else:
        emoji = EXCUSE_EMOJI[result["excuse_level"] - 1]
        msg = f"{emoji} {result['excuse']}"
        keyboard = [
            [InlineKeyboardButton("再誇一點 💣", callback_data=f"excuse_esc:{session_id}:{user_id}")],
            [InlineKeyboardButton("換個情況 🔄", callback_data="excuse_new")],
        ]

    await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if not await _check_enabled(update, context):
        return

    if data.startswith("mode:"):
        mode = data.split(":")[1]
        context.user_data["mode"] = mode
        prompt = "好，說吧，什麼東西要被評論？" if mode == "roast" else "說說看，什麼情況需要借口？"
        await query.message.reply_text(prompt)
        return

    if data == "reset":
        context.user_data.clear()
        await query.message.reply_text("好，重來，選一個。", reply_markup=_main_menu_markup())
        return

    if data == "excuse_new":
        context.user_data["mode"] = "excuse"
        await query.message.reply_text("好，說下一個情況。")
        return

    if data.startswith("retry:"):
        retry_id = data.split(":", 1)[1]
        # 先取出；若再次失敗，_do_* 會登記一筆新的重試動作
        last = context.user_data.get("retry_actions", {}).pop(retry_id, None)
        if not last:
            await query.message.reply_text("這個重試已經過期了，請重新輸入。")
            return
        if last["type"] == "roast":
            await _do_roast(update, context, last["user_id"], last["username"], last["text"])
        elif last["type"] == "excuse":
            await _do_excuse(update, context, last["user_id"], last["username"], last["text"])
        elif last["type"] == "roast_esc":
            await _do_roast_escalate(update, context, last["session_id"], last["user_id"])
        elif last["type"] == "excuse_esc":
            await _do_excuse_escalate(update, context, last["session_id"], last["user_id"])
        return

    if data.startswith("roast_esc:"):
        _, session_id, user_id = data.split(":")
        await _do_roast_escalate(update, context, session_id, user_id)
        return

    if data.startswith("excuse_esc:"):
        _, session_id, user_id = data.split(":")
        await _do_excuse_escalate(update, context, session_id, user_id)


async def _refresh_settings():
    # 超過 TTL 才重新從 DB 載入設定；讀取失敗時保留上次的值
    global _settings_loaded_at
    if time.monotonic() - _settings_loaded_at < SETTINGS_TTL:
        return
    from app.db.database import get_pool
    from app.services import app_settings as cfg
    try:
        pool = await get_pool()
        await cfg.load(pool)
    except Exception:
        logger.exception("重新載入設定失敗，沿用上次的值")
    # 失敗也更新時間，避免 DB 異常時每則訊息都重試
    _settings_loaded_at = time.monotonic()


async def _check_enabled(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    from app.services import app_settings as cfg
    await _refresh_settings()
    if not cfg.is_enabled("telegram_enabled"):
        await update.effective_message.reply_text("Telegram Bot 目前已停用。")
        return False
    return True


async def _post_init(application):
    # event loop 啟動後才載入設定，避免 asyncio event loop 衝突
    global _settings_loaded_at
    from app.db.database import get_pool
    from app.services import app_settings as cfg
    pool = await get_pool()
    await cfg.load(pool)
    _settings_loaded_at = time.monotonic()


def main():
    app = Application.builder().token(settings.telegram_bot_token).post_init(_post_init).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.run_polling()


if __name__ == "__main__":
    main()

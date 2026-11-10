# Telegram Bot：處理用戶訊息、模式選擇（嗆辣/借口）、升級按鈕互動
import logging
import secrets
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from app import bot_api
from app.bot_api import ApiError
from app.config import settings, MAX_INPUT_CHARS
from app.services import app_settings as cfg

PLATFORM = "telegram"

ROAST_EMOJI = ["😏", "😈", "🐍", "☠️", "👑"]
EXCUSE_EMOJI = ["📋", "🎭", "💣", "🌀", "🚀", "👑"]

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
    text = update.message.text.strip()
    if not text:
        return
    if len(text) > MAX_INPUT_CHARS:
        await update.message.reply_text(f"太長了，最多 {MAX_INPUT_CHARS} 字。")
        return

    if mode == "roast":
        await _do_roast(update, context, user.id, user.username, text)
    else:
        await _do_excuse(update, context, user.id, user.username, text)


async def _do_roast(update, context, user_id, username, text):
    action = {"type": "roast", "user_id": user_id, "username": username, "text": text}
    await context.bot.send_chat_action(update.effective_chat.id, "typing")
    try:
        data = await bot_api.post("/roast/start", {
            "platform": PLATFORM,
            "user_id": str(user_id),
            "username": username,
            "content": text,
        })
    except ApiError as err:
        markup = _retry_markup(context, action) if err.retryable else None
        await update.effective_message.reply_text(err.message, reply_markup=markup)
        return

    emoji = ROAST_EMOJI[data["venom_level"] - 1]
    keyboard = []
    if data["can_escalate"]:
        keyboard.append([InlineKeyboardButton(
            "再毒一點 🐍",
            callback_data=f"roast_esc:{data['session_id']}",
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
        data = await bot_api.post("/excuse/start", {
            "platform": PLATFORM,
            "user_id": str(user_id),
            "username": username,
            "situation": text,
        })
    except ApiError as err:
        markup = _retry_markup(context, action) if err.retryable else None
        await update.effective_message.reply_text(err.message, reply_markup=markup)
        return

    emoji = EXCUSE_EMOJI[data["excuse_level"] - 1]
    keyboard = [
        [InlineKeyboardButton("再誇一點 🎭", callback_data=f"excuse_esc:{data['session_id']}")],
        [InlineKeyboardButton("換個情況 🔄", callback_data="excuse_new")],
    ]

    await update.effective_message.reply_text(
        f"{emoji} {data['excuse']}",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def _report_escalate_error(update, context, err: ApiError, action):
    query = update.callback_query
    if err.retryable:
        # 暫時性錯誤：在原訊息上改為重試按鈕，重試時 callback 的 message 即為原本那則訊息
        await query.edit_message_text(err.message, reply_markup=_retry_markup(context, action))
    else:
        # 重試也沒用的錯誤（按太快、不是自己的對話…）：另外回一則，不要把原本那則回覆蓋掉
        await query.message.reply_text(err.message)


async def _do_roast_escalate(update, context, session_id):
    query = update.callback_query
    action = {"type": "roast_esc", "session_id": session_id}
    await context.bot.send_chat_action(update.effective_chat.id, "typing")
    try:
        # user_id 用「按下按鈕的人」而不是按鈕裡帶的值，backend 會擋掉不是對話主人的升級
        result = await bot_api.post("/roast/escalate", {
            "platform": PLATFORM,
            "user_id": str(query.from_user.id),
            "session_id": session_id,
        })
    except ApiError as err:
        await _report_escalate_error(update, context, err, action)
        return

    if result["is_nuclear"]:
        msg = f"💥 {result['roast']}"
        keyboard = [[InlineKeyboardButton("換個目標 🎯", callback_data="reset")]]
    else:
        emoji = ROAST_EMOJI[result["venom_level"] - 1]
        msg = f"{emoji} {result['roast']}"
        keyboard = [
            [InlineKeyboardButton("再毒一點 🐍", callback_data=f"roast_esc:{session_id}")],
            [InlineKeyboardButton("換個目標 🎯", callback_data="reset")],
        ]

    await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))


async def _do_excuse_escalate(update, context, session_id):
    query = update.callback_query
    action = {"type": "excuse_esc", "session_id": session_id}
    await context.bot.send_chat_action(update.effective_chat.id, "typing")
    try:
        result = await bot_api.post("/excuse/escalate", {
            "platform": PLATFORM,
            "user_id": str(query.from_user.id),
            "session_id": session_id,
        })
    except ApiError as err:
        await _report_escalate_error(update, context, err, action)
        return

    if result["is_nuclear"]:
        msg = f"💣 {result['excuse']}"
        keyboard = [[InlineKeyboardButton("換個情況 🔄", callback_data="excuse_new")]]
    else:
        emoji = EXCUSE_EMOJI[result["excuse_level"] - 1]
        msg = f"{emoji} {result['excuse']}"
        keyboard = [
            [InlineKeyboardButton("再誇一點 💣", callback_data=f"excuse_esc:{session_id}")],
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
            await _do_roast_escalate(update, context, last["session_id"])
        elif last["type"] == "excuse_esc":
            await _do_excuse_escalate(update, context, last["session_id"])
        return

    # 格式是 '<動作>:<session_id>'。舊版按鈕後面還多帶一段 user_id，一樣能解析（多的部分不用）
    if data.startswith("roast_esc:"):
        await _do_roast_escalate(update, context, data.split(":")[1])
        return

    if data.startswith("excuse_esc:"):
        await _do_excuse_escalate(update, context, data.split(":")[1])


async def _check_enabled(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    await cfg.reload_if_stale(bot_api.SETTINGS_TTL)
    if not cfg.is_enabled("telegram_enabled"):
        await update.effective_message.reply_text("Telegram Bot 目前已停用。")
        return False
    return True


async def _post_init(application):
    # event loop 啟動後才載入設定，避免 asyncio event loop 衝突
    from app.db.database import get_pool
    pool = await get_pool()
    await cfg.load(pool)


def main():
    app = Application.builder().token(settings.telegram_bot_token).post_init(_post_init).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.run_polling()


if __name__ == "__main__":
    main()

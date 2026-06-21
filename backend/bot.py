# Telegram Bot：處理用戶訊息、模式選擇（嗆辣/借口）、升級按鈕互動
import httpx
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from app.config import settings

API_BASE = f"{settings.api_base_url}/api"

ROAST_EMOJI = ["😏", "😈", "🐍", "☠️", "👑"]
EXCUSE_EMOJI = ["📋", "🎭", "💣", "🌀", "🚀", "👑"]

MAIN_MENU = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("嗆我 🐍", callback_data="mode:roast"),
        InlineKeyboardButton("幫我找借口 📋", callback_data="mode:excuse"),
    ]
])


def _main_menu_markup():
    return MAIN_MENU


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("你好，想幹嘛？", reply_markup=_main_menu_markup())


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(f"{API_BASE}/roast/start", json={
                "content": text,
                "user_id": user_id,
                "username": username,
            })
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        await update.message.reply_text("出了點問題，稍後再試。")
        return

    emoji = ROAST_EMOJI[data["venom_level"] - 1]
    keyboard = []
    if data["can_escalate"]:
        keyboard.append([InlineKeyboardButton(
            "再毒一點 🐍",
            callback_data=f"roast_esc:{data['session_id']}:{user_id}",
        )])
    keyboard.append([InlineKeyboardButton("換個目標 🎯", callback_data="reset")])

    await update.message.reply_text(
        f"{emoji} {data['roast']}",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def _do_excuse(update, context, user_id, username, text):
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(f"{API_BASE}/excuse/start", json={
                "situation": text,
                "user_id": user_id,
                "username": username,
            })
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        await update.message.reply_text("出了點問題，稍後再試。")
        return

    emoji = EXCUSE_EMOJI[data["excuse_level"] - 1]
    keyboard = [
        [InlineKeyboardButton("再誇一點 🎭", callback_data=f"excuse_esc:{data['session_id']}:{user_id}")],
        [InlineKeyboardButton("換個情況 🔄", callback_data="excuse_new")],
    ]

    await update.message.reply_text(
        f"{emoji} {data['excuse']}",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

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

    if data.startswith("roast_esc:"):
        _, session_id, user_id = data.split(":")
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(f"{API_BASE}/roast/escalate", json={
                    "session_id": session_id,
                    "user_id": int(user_id),
                })
                resp.raise_for_status()
                result = resp.json()
        except Exception:
            await query.message.reply_text("出了點問題，稍後再試。")
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
        return

    if data.startswith("excuse_esc:"):
        _, session_id, user_id = data.split(":")
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(f"{API_BASE}/excuse/escalate", json={
                    "session_id": session_id,
                    "user_id": int(user_id),
                })
                resp.raise_for_status()
                result = resp.json()
        except Exception:
            await query.message.reply_text("出了點問題，稍後再試。")
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


async def _check_enabled(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    from app.services import app_settings as cfg
    if not cfg.is_enabled("telegram_enabled"):
        await update.message.reply_text("Telegram Bot 目前已停用。")
        return False
    return True


async def _post_init(application):
    # event loop 啟動後才載入設定，避免 asyncio event loop 衝突
    from app.db.database import get_pool
    from app.services import app_settings as cfg
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

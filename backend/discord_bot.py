# Discord Bot：slash command /roast 與 /excuse，支援升級按鈕（discord.ui.View）
# 跟 Telegram bot 一樣透過 backend 的內部端點生成回覆，對話紀錄、等級規則、頻率限制才會一致
import asyncio
import discord
from discord import app_commands
from app import bot_api, emoji
from app.bot_api import ApiError
from app.config import settings, MAX_INPUT_CHARS
from app.services import app_settings as cfg

PLATFORM = "discord"
DISCORD_MESSAGE_LIMIT = 2000

ESCALATE_LABEL = {"roast": "再毒一點 🐍", "excuse": "再誇一點 🎭"}
# backend 回應裡「回覆內容 / 等級」的欄位名稱
TEXT_FIELD = {"roast": "roast", "excuse": "excuse"}
LEVEL_FIELD = {"roast": "venom_level", "excuse": "excuse_level"}


async def _is_enabled() -> bool:
    await cfg.reload_if_stale(bot_api.SETTINGS_TTL)
    return cfg.is_enabled("discord_enabled")


def _format(mode: str, data: dict) -> str:
    prefix = emoji.for_reply(mode, data[LEVEL_FIELD[mode]], data["is_nuclear"])
    return f"{prefix} {data[TEXT_FIELD[mode]]}"[:DISCORD_MESSAGE_LIMIT]


async def _send_reply(followup: discord.Webhook, mode: str, owner_id: int, data: dict):
    kwargs = {}
    if data["can_escalate"]:
        kwargs["view"] = EscalateView(owner_id, mode, data["session_id"])
    await followup.send(content=_format(mode, data), **kwargs)


class EscalateView(discord.ui.View):
    def __init__(self, owner_id: int, mode: str, session_id: str):
        super().__init__(timeout=300)
        self.owner_id = owner_id
        self.mode = mode
        self.session_id = session_id
        self.escalate.label = ESCALATE_LABEL[mode]

    @discord.ui.button(label="再毒一點 🐍", style=discord.ButtonStyle.danger)
    async def escalate(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("這不是你的對話。", ephemeral=True)
            return
        if not await _is_enabled():
            await interaction.response.send_message("Discord Bot 目前已停用。", ephemeral=True)
            return

        # 按鈕（component）互動預設 defer() 是 deferred_message_update，不會顯示任何等待提示；
        # 要跟 slash command 一樣讓 Discord 顯示原生「思考中」，component 互動要帶 thinking=True
        await interaction.response.defer(thinking=True)

        try:
            data = await bot_api.post(f"/{self.mode}/escalate", {
                "platform": PLATFORM,
                "user_id": str(interaction.user.id),
                "session_id": self.session_id,
            })
        except ApiError as err:
            await interaction.followup.send(f"😵 {err.message}")
            return

        await _send_reply(interaction.followup, self.mode, self.owner_id, data)


class TongueBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()

    async def on_ready(self):
        print(f"Discord Bot 已上線：{self.user}")


client = TongueBot()


async def _start_conversation(interaction: discord.Interaction, mode: str, text: str):
    # /roast 與 /excuse 共用：開一場新對話並送出第一則回覆
    if not await _is_enabled():
        await interaction.response.send_message("Discord Bot 目前已停用。", ephemeral=True)
        return
    text = text.strip()
    if not text:
        await interaction.response.send_message("你什麼都沒說。", ephemeral=True)
        return
    if len(text) > MAX_INPUT_CHARS:
        await interaction.response.send_message(f"太長了，最多 {MAX_INPUT_CHARS} 字。", ephemeral=True)
        return

    await interaction.response.defer()

    payload = {
        "platform": PLATFORM,
        "user_id": str(interaction.user.id),
        "username": interaction.user.name,
    }
    payload["content" if mode == "roast" else "situation"] = text
    try:
        data = await bot_api.post(f"/{mode}/start", payload)
    except ApiError as err:
        await interaction.followup.send(f"😵 {err.message}")
        return

    await _send_reply(interaction.followup, mode, interaction.user.id, data)


@client.tree.command(name="roast", description="嗆辣評論你說的話")
@app_commands.describe(text="要被評論的東西")
async def roast_cmd(interaction: discord.Interaction, text: str):
    await _start_conversation(interaction, "roast", text)


@client.tree.command(name="excuse", description="幫你想借口")
@app_commands.describe(situation="什麼情況需要借口")
async def excuse_cmd(interaction: discord.Interaction, situation: str):
    await _start_conversation(interaction, "excuse", situation)


def main():
    async def _start():
        from app.db.database import get_pool
        await cfg.load(await get_pool())
        await client.start(settings.discord_bot_token)

    asyncio.run(_start())


if __name__ == "__main__":
    main()

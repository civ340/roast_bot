import asyncio
import discord
from discord import app_commands
from app.config import settings
from app.services import app_settings as cfg
from app.services import llm

ROAST_EMOJI = ["😏", "😈", "🐍", "☠️", "👑"]
EXCUSE_EMOJI = ["📋", "🎭", "💣", "🌀", "🚀", "👑"]

# in-memory session store: {user_id: {session_id, last_input, last_output, mode, level}}
_sessions: dict[int, dict] = {}


class EscalateView(discord.ui.View):
    def __init__(self, user_id: int, mode: str):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.mode = mode

    @discord.ui.button(label="再毒一點 🐍", style=discord.ButtonStyle.danger, custom_id="escalate")
    async def escalate(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("這不是你的對話。", ephemeral=True)
            return

        session = _sessions.get(self.user_id)
        if not session:
            await interaction.response.send_message("找不到對話，請重新開始。", ephemeral=True)
            return

        await interaction.response.defer()

        new_level = session["level"] + 1
        is_roast = session["mode"] == "roast"

        if is_roast:
            is_nuclear = new_level >= 5
            result = await llm.generate_roast(
                session["last_input"], new_level,
                is_nuclear=is_nuclear,
                previous_output=session["last_output"],
            )
            emoji = "💥" if is_nuclear else ROAST_EMOJI[min(new_level - 1, 4)]
        else:
            is_nuclear = new_level >= 6
            result = await llm.generate_excuse(
                session["last_input"], new_level,
                previous_output=session["last_output"],
            )
            emoji = EXCUSE_EMOJI[min(new_level - 1, 5)]

        session["last_output"] = result
        session["level"] = new_level

        view = EscalateView(self.user_id, session["mode"]) if not is_nuclear else discord.ui.View()
        if not is_nuclear:
            label = "再毒一點 🐍" if is_roast else "再誇一點 🎭"
            view.children[0].label = label  # type: ignore

        await interaction.followup.send(f"{emoji} {result}", view=view)


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


@client.tree.command(name="roast", description="毒舌評論你說的話")
@app_commands.describe(text="要被評論的東西")
async def roast_cmd(interaction: discord.Interaction, text: str):
    if not cfg.is_enabled("discord_enabled"):
        await interaction.response.send_message("Discord Bot 目前已停用。", ephemeral=True)
        return

    await interaction.response.defer()
    result = await llm.generate_roast(text, venom_level=1)

    _sessions[interaction.user.id] = {
        "mode": "roast", "level": 1,
        "last_input": text, "last_output": result,
    }

    view = EscalateView(interaction.user.id, "roast")
    await interaction.followup.send(f"😏 {result}", view=view)


@client.tree.command(name="excuse", description="幫你想借口")
@app_commands.describe(situation="什麼情況需要借口")
async def excuse_cmd(interaction: discord.Interaction, situation: str):
    if not cfg.is_enabled("discord_enabled"):
        await interaction.response.send_message("Discord Bot 目前已停用。", ephemeral=True)
        return

    await interaction.response.defer()
    result = await llm.generate_excuse(situation, excuse_level=1)

    _sessions[interaction.user.id] = {
        "mode": "excuse", "level": 1,
        "last_input": situation, "last_output": result,
    }

    view = EscalateView(interaction.user.id, "excuse")
    view.children[0].label = "再誇一點 🎭"  # type: ignore
    await interaction.followup.send(f"📋 {result}", view=view)


def main():
    async def _start():
        pool_task = asyncio.create_task(_load_settings())
        await pool_task
        await client.start(settings.discord_bot_token)

    async def _load_settings():
        from app.db.database import get_pool
        pool = await get_pool()
        await cfg.load(pool)

    asyncio.run(_start())


if __name__ == "__main__":
    main()

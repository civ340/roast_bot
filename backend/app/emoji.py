# 各等級回覆前面的表情符號（LINE 與 Discord 共用）

ROAST_EMOJI = ["😏", "😈", "🐍", "☠️", "👑"]
EXCUSE_EMOJI = ["📋", "🎭", "💣", "🌀", "🚀", "👑"]


def for_reply(mode: str, level: int, is_nuclear: bool) -> str:
    if mode == "roast":
        return "💥" if is_nuclear else ROAST_EMOJI[max(0, min(level, len(ROAST_EMOJI)) - 1)]
    return EXCUSE_EMOJI[max(0, min(level, len(EXCUSE_EMOJI)) - 1)]

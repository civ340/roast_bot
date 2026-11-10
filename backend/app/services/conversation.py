# 嗆辣 / 借口的核心流程。三個平台都走這裡（Telegram、Discord 經 /api/roast、/api/excuse，
# LINE webhook 在 backend 行程內直接呼叫），等級規則、頻率限制、對話紀錄才會一致。
from __future__ import annotations
from dataclasses import dataclass
from uuid import UUID
import asyncpg
from app.errors import AlreadyMaxed, EscalationConflict, NotYourSession, SessionNotFound
from app.services import llm, memory, ratelimit

MAX_ROAST_LEVEL = 5   # 到 5 之後再升一次是核彈（等級維持 5）
MAX_EXCUSE_LEVEL = 6  # 升到 6 就是最終級


@dataclass
class Reply:
    session_id: str
    text: str
    level: int
    can_escalate: bool
    is_nuclear: bool


def make_user_key(platform: str, user_id: str) -> str:
    return f"{platform}:{user_id}"


async def start(pool: asyncpg.Pool, mode: str, user_key: str, username: str | None, text: str) -> Reply:
    # 開一場新對話，從等級 1 生成第一則回覆
    ratelimit.check(user_key)
    await memory.upsert_user(pool, user_key, username)

    if mode == "roast":
        output = await llm.generate_roast(text, venom_level=1)
    else:
        output = await llm.generate_excuse(text, excuse_level=1)

    session_id = await memory.create_session_with_exchange(pool, user_key, mode, text, output)
    return Reply(session_id=str(session_id), text=output, level=1, can_escalate=True, is_nuclear=False)


async def escalate(pool: asyncpg.Pool, mode: str, user_key: str, session_id: UUID) -> Reply:
    # 把現有 session 升一級，帶入上一則回覆讓模型知道要超越它
    session = await memory.get_session(pool, session_id)
    if not session or session["mode"] != mode:
        raise SessionNotFound()
    # 只有開這場對話的人能升級（群組裡別人按了按鈕不算）
    if session["user_id"] != user_key:
        raise NotYourSession()
    if session["nuclear_triggered"]:
        raise AlreadyMaxed()

    ratelimit.check(user_key)

    current_level = session["venom_level"]
    if mode == "roast":
        is_nuclear = current_level >= MAX_ROAST_LEVEL
        new_level = MAX_ROAST_LEVEL if is_nuclear else current_level + 1
    else:
        new_level = min(current_level + 1, MAX_EXCUSE_LEVEL)
        is_nuclear = new_level >= MAX_EXCUSE_LEVEL

    last_user_input, last_bot_output = await memory.last_exchange(pool, session_id)
    if last_user_input is None:
        raise SessionNotFound()

    if mode == "roast":
        output = await llm.generate_roast(
            last_user_input, new_level, is_nuclear=is_nuclear, previous_output=last_bot_output,
        )
    else:
        output = await llm.generate_excuse(
            last_user_input, excuse_level=new_level, previous_output=last_bot_output,
        )

    # 等級與核彈旗標在 LLM 成功後才寫回 DB，避免失敗時等級被跳過或卡在核彈狀態
    advanced = await memory.advance_session(
        pool, session_id, user_key,
        expected_level=current_level, new_level=new_level, is_nuclear=is_nuclear,
        bot_output=output, track_max_level=(mode == "roast"),
    )
    if not advanced:
        raise EscalationConflict()

    return Reply(
        session_id=str(session_id), text=output, level=new_level,
        can_escalate=not is_nuclear, is_nuclear=is_nuclear,
    )

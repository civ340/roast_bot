# 借口生成路由：處理開始借口與升級請求（最高 6 級）
from uuid import UUID
from fastapi import APIRouter, HTTPException
from app.db.database import get_pool
from app.models.schemas import ExcuseRequest, ExcuseResponse, EscalateRequest
from app.services import llm, memory

router = APIRouter()

MAX_EXCUSE_LEVEL = 6


@router.post("/start", response_model=ExcuseResponse)
async def start_excuse(req: ExcuseRequest):
    # 建立新 session，從等級 1 生成第一個借口
    pool = await get_pool()
    await memory.get_or_create_user(pool, req.user_id, req.username)
    session_id = await memory.create_session(pool, req.user_id, start_level=1, mode="excuse")

    excuse_text = await llm.generate_excuse(req.situation, excuse_level=1)

    await memory.save_message(pool, session_id, req.user_id, "user", req.situation, 1)
    await memory.save_message(pool, session_id, req.user_id, "bot", excuse_text, 1)

    return ExcuseResponse(
        session_id=session_id,
        excuse=excuse_text,
        excuse_level=1,
        can_escalate=True,
        is_nuclear=False,
    )


@router.post("/escalate", response_model=ExcuseResponse)
async def escalate_excuse(req: EscalateRequest):
    # 借口等級 +1，帶入上一條借口讓模型知道要更誇張
    pool = await get_pool()
    session = await memory.get_session(pool, req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session["nuclear_triggered"]:
        raise HTTPException(status_code=400, detail="Already at max level")

    current_level = session["venom_level"]
    new_level = current_level + 1
    is_nuclear = new_level >= MAX_EXCUSE_LEVEL

    await memory.set_level(pool, req.session_id, new_level)
    if is_nuclear:
        await memory.trigger_nuclear(pool, req.session_id)

    async with (await get_pool()).acquire() as conn:
        last_user_input = await conn.fetchval(
            "SELECT content FROM messages WHERE session_id = $1 AND role = 'user' ORDER BY created_at DESC LIMIT 1",
            UUID(req.session_id),
        )
        last_bot_output = await conn.fetchval(
            "SELECT content FROM messages WHERE session_id = $1 AND role = 'bot' ORDER BY created_at DESC LIMIT 1",
            UUID(req.session_id),
        )

    excuse_text = await llm.generate_excuse(
        last_user_input,
        excuse_level=new_level,
        previous_output=last_bot_output,
    )
    await memory.save_message(pool, req.session_id, req.user_id, "bot", excuse_text, new_level)

    return ExcuseResponse(
        session_id=req.session_id,
        excuse=excuse_text,
        excuse_level=new_level,
        can_escalate=not is_nuclear,
        is_nuclear=is_nuclear,
    )

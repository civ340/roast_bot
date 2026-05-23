from uuid import UUID
from fastapi import APIRouter, HTTPException
from app.db.database import get_pool
from app.models.schemas import RoastRequest, RoastResponse, EscalateRequest
from app.services import llm, memory

router = APIRouter()


@router.post("/start", response_model=RoastResponse)
async def start_roast(req: RoastRequest):
    pool = await get_pool()
    await memory.get_or_create_user(pool, req.user_id, req.username)
    session_id = await memory.create_session(pool, req.user_id, start_level=1, mode="roast")

    roast_text = await llm.generate_roast(req.content, venom_level=1)

    await memory.save_message(pool, session_id, req.user_id, "user", req.content, 1)
    await memory.save_message(pool, session_id, req.user_id, "bot", roast_text, 1)

    return RoastResponse(
        session_id=session_id,
        roast=roast_text,
        venom_level=1,
        can_escalate=True,
        is_nuclear=False,
    )


@router.post("/escalate", response_model=RoastResponse)
async def escalate_roast(req: EscalateRequest):
    pool = await get_pool()
    session = await memory.get_session(pool, req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session["nuclear_triggered"]:
        raise HTTPException(status_code=400, detail="Already at nuclear level")

    new_level = await memory.escalate_venom(pool, req.session_id, req.user_id)

    is_nuclear = False
    if new_level is None:
        new_level = 5
        is_nuclear = True
        await memory.trigger_nuclear(pool, req.session_id)

    async with pool.acquire() as conn:
        last_user_input = await conn.fetchval(
            "SELECT content FROM messages WHERE session_id = $1 AND role = 'user' ORDER BY created_at DESC LIMIT 1",
            UUID(req.session_id),
        )
        last_bot_output = await conn.fetchval(
            "SELECT content FROM messages WHERE session_id = $1 AND role = 'bot' ORDER BY created_at DESC LIMIT 1",
            UUID(req.session_id),
        )

    roast_text = await llm.generate_roast(
        last_user_input,
        new_level,
        is_nuclear=is_nuclear,
        previous_output=last_bot_output,
    )
    await memory.save_message(pool, req.session_id, req.user_id, "bot", roast_text, new_level)

    return RoastResponse(
        session_id=req.session_id,
        roast=roast_text,
        venom_level=new_level,
        can_escalate=not is_nuclear,
        is_nuclear=is_nuclear,
    )

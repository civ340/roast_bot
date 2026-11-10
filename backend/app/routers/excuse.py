# 借口生成路由：處理開始借口與升級請求，最高 6 級（流程在 services/conversation.py）
from fastapi import APIRouter
from app.db.database import get_pool
from app.models.schemas import ExcuseRequest, ExcuseResponse, EscalateRequest
from app.services import conversation

router = APIRouter()


def _response(reply: conversation.Reply) -> ExcuseResponse:
    return ExcuseResponse(
        session_id=reply.session_id,
        excuse=reply.text,
        excuse_level=reply.level,
        can_escalate=reply.can_escalate,
        is_nuclear=reply.is_nuclear,
    )


@router.post("/start", response_model=ExcuseResponse)
async def start_excuse(req: ExcuseRequest):
    # 建立新 session，從等級 1 生成第一個借口
    pool = await get_pool()
    user_key = conversation.make_user_key(req.platform, req.user_id)
    return _response(await conversation.start(pool, "excuse", user_key, req.username, req.situation))


@router.post("/escalate", response_model=ExcuseResponse)
async def escalate_excuse(req: EscalateRequest):
    # 借口等級 +1，帶入上一條借口讓模型知道要更誇張
    pool = await get_pool()
    user_key = conversation.make_user_key(req.platform, req.user_id)
    return _response(await conversation.escalate(pool, "excuse", user_key, req.session_id))

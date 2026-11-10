# 嗆辣功能路由：處理開始評論與升級請求（流程在 services/conversation.py）
from fastapi import APIRouter
from app.db.database import get_pool
from app.models.schemas import RoastRequest, RoastResponse, EscalateRequest
from app.services import conversation

router = APIRouter()


def _response(reply: conversation.Reply) -> RoastResponse:
    return RoastResponse(
        session_id=reply.session_id,
        roast=reply.text,
        venom_level=reply.level,
        can_escalate=reply.can_escalate,
        is_nuclear=reply.is_nuclear,
    )


@router.post("/start", response_model=RoastResponse)
async def start_roast(req: RoastRequest):
    # 建立新 session，從等級 1 開始生成第一條評論
    pool = await get_pool()
    user_key = conversation.make_user_key(req.platform, req.user_id)
    return _response(await conversation.start(pool, "roast", user_key, req.username, req.content))


@router.post("/escalate", response_model=RoastResponse)
async def escalate_roast(req: EscalateRequest):
    # 將現有 session 的嗆辣等級 +1；已在等級 5 時觸發核彈終極模式
    pool = await get_pool()
    user_key = conversation.make_user_key(req.platform, req.user_id)
    return _response(await conversation.escalate(pool, "roast", user_key, req.session_id))

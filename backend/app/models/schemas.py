# API 請求與回應的資料格式定義（Pydantic 自動做型別驗證）
from pydantic import BaseModel
from datetime import datetime
from uuid import UUID


# 嗆辣：開始一場新的評論
class RoastRequest(BaseModel):
    content: str
    user_id: int
    username: str | None = None


# 嗆辣：回傳評論結果
class RoastResponse(BaseModel):
    session_id: str
    roast: str
    venom_level: int    # 1~5
    can_escalate: bool  # 是否還能再毒一點
    is_nuclear: bool    # 是否已到核彈等級


# 嗆辣 & 借口共用：升級請求
class EscalateRequest(BaseModel):
    session_id: str
    user_id: int


# 借口：開始一個新的借口情境
class ExcuseRequest(BaseModel):
    situation: str
    user_id: int
    username: str | None = None


# 借口：回傳借口結果
class ExcuseResponse(BaseModel):
    session_id: str
    excuse: str
    excuse_level: int   # 1~6
    can_escalate: bool
    is_nuclear: bool


# 後台查看對話記錄用
class ConversationRecord(BaseModel):
    id: int
    session_id: UUID
    user_id: int
    role: str           # 'user' | 'bot'
    content: str
    venom_level: int | None
    created_at: datetime

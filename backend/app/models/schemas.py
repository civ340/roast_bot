# API 請求與回應的資料格式定義（Pydantic 自動做型別驗證）
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from app.config import MAX_INPUT_CHARS

Platform = Literal["telegram", "line", "discord"]


class _UserRequest(BaseModel):
    # user_id 是該平台上的用戶 ID；Telegram / Discord 是數字、LINE 是字串，一律當字串處理
    model_config = ConfigDict(coerce_numbers_to_str=True, str_strip_whitespace=True)

    platform: Platform = "telegram"
    user_id: str = Field(min_length=1, max_length=64)


# 嗆辣：開始一場新的評論
class RoastRequest(_UserRequest):
    content: str = Field(min_length=1, max_length=MAX_INPUT_CHARS)
    username: str | None = None


# 嗆辣：回傳評論結果
class RoastResponse(BaseModel):
    session_id: str
    roast: str
    venom_level: int    # 1~5
    can_escalate: bool  # 是否還能再毒一點
    is_nuclear: bool    # 是否已到核彈等級


# 嗆辣 & 借口共用：升級請求
class EscalateRequest(_UserRequest):
    session_id: UUID


# 借口：開始一個新的借口情境
class ExcuseRequest(_UserRequest):
    situation: str = Field(min_length=1, max_length=MAX_INPUT_CHARS)
    username: str | None = None


# 借口：回傳借口結果
class ExcuseResponse(BaseModel):
    session_id: str
    excuse: str
    excuse_level: int   # 1~6
    can_escalate: bool
    is_nuclear: bool

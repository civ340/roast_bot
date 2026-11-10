# 後台設定路由：讓管理介面讀取與更新 LLM 設定、平台開關
from typing import Literal
from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.db.database import get_pool
from app.services import app_settings as cfg

router = APIRouter()


class SettingsPayload(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    llm_provider:     Literal["ollama", "openai", "anthropic"] | None = None
    llm_model:        str | None = Field(default=None, min_length=1, max_length=200)
    llm_api_key:      str | None = Field(default=None, max_length=500)  # None 或 '****' 代表不更新，'' 代表清除
    llm_base_url:     str | None = Field(default=None, max_length=500)
    telegram_enabled: bool | None = None
    line_enabled:     bool | None = None
    discord_enabled:  bool | None = None

    @field_validator("llm_base_url")
    @classmethod
    def _check_base_url(cls, value: str | None) -> str | None:
        # 後台每次儲存都會把這個欄位一起送來（就算目前不是用 Ollama），所以空字串要放行
        if not value:
            return value
        if not value.startswith(("http://", "https://")):
            raise ValueError("llm_base_url 必須以 http:// 或 https:// 開頭")
        return value.rstrip("/")


@router.get("")
async def get_settings():
    # 回傳所有設定，api_key 已設定時遮罩為 ****
    return cfg.all_public()


@router.put("")
async def update_settings(payload: SettingsPayload):
    # 只更新有傳入的欄位，api_key 為 **** 時跳過（代表前端顯示遮罩未修改）
    pool = await get_pool()
    updates: dict[str, str] = {}

    if payload.llm_provider is not None:
        updates["llm_provider"] = payload.llm_provider
    if payload.llm_model is not None:
        updates["llm_model"] = payload.llm_model
    # None / '****' 視為未修改；空字串代表清除已存的 key
    if payload.llm_api_key not in (None, "****"):
        updates["llm_api_key"] = payload.llm_api_key
    if payload.llm_base_url is not None:
        updates["llm_base_url"] = payload.llm_base_url
    if payload.telegram_enabled is not None:
        updates["telegram_enabled"] = str(payload.telegram_enabled).lower()
    if payload.line_enabled is not None:
        updates["line_enabled"] = str(payload.line_enabled).lower()
    if payload.discord_enabled is not None:
        updates["discord_enabled"] = str(payload.discord_enabled).lower()

    if updates:
        await cfg.save(pool, updates)

    return cfg.all_public()

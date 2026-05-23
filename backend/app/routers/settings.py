from fastapi import APIRouter
from pydantic import BaseModel
from app.db.database import get_pool
from app.services import app_settings as cfg

router = APIRouter()


class SettingsPayload(BaseModel):
    llm_provider:     str | None = None
    llm_model:        str | None = None
    llm_api_key:      str | None = None
    llm_base_url:     str | None = None
    telegram_enabled: bool | None = None
    line_enabled:     bool | None = None
    discord_enabled:  bool | None = None


@router.get("")
async def get_settings():
    return cfg.all_public()


@router.put("")
async def update_settings(payload: SettingsPayload):
    pool = await get_pool()
    updates: dict[str, str] = {}

    if payload.llm_provider is not None:
        updates["llm_provider"] = payload.llm_provider
    if payload.llm_model is not None:
        updates["llm_model"] = payload.llm_model
    if payload.llm_api_key is not None and payload.llm_api_key != "****":
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

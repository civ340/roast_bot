# 後台設定管理：從 DB 讀取設定並快取在記憶體，避免每次都查資料庫
from __future__ import annotations
import asyncpg

_cache: dict[str, str] = {}

# 預設值，DB 沒有對應 key 時使用
DEFAULTS: dict[str, str] = {
    "llm_provider":     "ollama",
    "llm_model":        "llama3",
    "llm_api_key":      "",
    "llm_base_url":     "http://host.docker.internal:11434",
    "telegram_enabled": "true",
    "line_enabled":     "false",
    "discord_enabled":  "false",
}


async def load(pool: asyncpg.Pool) -> None:
    # 應用程式啟動時載入所有設定到記憶體
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT key, value FROM app_settings")
    for row in rows:
        _cache[row["key"]] = row["value"]


def get(key: str) -> str:
    # 取得單一設定值
    return _cache.get(key, DEFAULTS.get(key, ""))


def is_enabled(key: str) -> bool:
    # 取得布林類設定（telegram_enabled 等）
    return get(key).lower() == "true"


async def save(pool: asyncpg.Pool, data: dict[str, str]) -> None:
    # 寫入 DB 並同步更新記憶體快取
    async with pool.acquire() as conn:
        for k, v in data.items():
            await conn.execute(
                """
                INSERT INTO app_settings (key, value, updated_at)
                VALUES ($1, $2, NOW())
                ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()
                """,
                k, v,
            )
    _cache.update(data)


def all_public() -> dict[str, str]:
    # 回傳所有設定，api_key 已設定時遮罩為 ****
    result = {**DEFAULTS, **_cache}
    if result.get("llm_api_key"):
        result["llm_api_key"] = "****"
    return result

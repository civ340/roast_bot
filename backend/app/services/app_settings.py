from __future__ import annotations
import asyncpg

_cache: dict[str, str] = {}

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
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT key, value FROM app_settings")
    for row in rows:
        _cache[row["key"]] = row["value"]


def get(key: str) -> str:
    return _cache.get(key, DEFAULTS.get(key, ""))


def is_enabled(key: str) -> bool:
    return get(key).lower() == "true"


async def save(pool: asyncpg.Pool, data: dict[str, str]) -> None:
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
    result = {**DEFAULTS, **_cache}
    if result.get("llm_api_key"):
        result["llm_api_key"] = "****"
    return result

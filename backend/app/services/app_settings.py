# 後台設定管理：從 DB 讀取設定並快取在記憶體，避免每次都查資料庫
from __future__ import annotations
import base64
import hashlib
import logging
import time
import asyncpg
from cryptography.fernet import Fernet, InvalidToken
from app.config import settings as env

logger = logging.getLogger(__name__)

_cache: dict[str, str] = {}
_loaded_at = 0.0

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

# 這些 key 的值加密後才寫進 DB（快取裡放的也是密文，要用 get_secret 取明文）
SECRET_KEYS = {"llm_api_key"}
_ENC_PREFIX = "enc:v1:"


def _fernet() -> Fernet:
    # 加密金鑰由 API_SECRET_KEY 衍生；換掉 API_SECRET_KEY 之後舊密文會解不開，需要到後台重新輸入 API key
    digest = hashlib.sha256(b"tongue-settings-v1:" + env.api_secret_key.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def _encrypt(value: str) -> str:
    if not value or value.startswith(_ENC_PREFIX):
        return value
    return _ENC_PREFIX + _fernet().encrypt(value.encode()).decode()


def _decrypt(value: str) -> str:
    if not value.startswith(_ENC_PREFIX):
        return value  # 舊版留下的明文
    try:
        return _fernet().decrypt(value[len(_ENC_PREFIX):].encode()).decode()
    except InvalidToken:
        logger.error("設定值解密失敗（API_SECRET_KEY 是否換過？），請到後台重新輸入 API Key")
        return ""


async def load(pool: asyncpg.Pool) -> None:
    # 應用程式啟動時載入所有設定到記憶體
    global _loaded_at
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT key, value FROM app_settings")
    for row in rows:
        _cache[row["key"]] = row["value"]
    _loaded_at = time.monotonic()


async def reload_if_stale(ttl_seconds: float) -> None:
    # 給獨立行程的 bot 用：超過 TTL 才重新從 DB 載入，才能反映後台的開關變更。
    # 讀取失敗時保留上次的值，而且一樣更新時間，避免 DB 異常時每則訊息都重試。
    global _loaded_at
    if time.monotonic() - _loaded_at < ttl_seconds:
        return
    from app.db.database import get_pool
    try:
        await load(await get_pool())
    except Exception:
        logger.exception("重新載入設定失敗，沿用上次的值")
        _loaded_at = time.monotonic()


def get(key: str) -> str:
    # 取得單一設定值（SECRET_KEYS 裡的 key 拿到的是密文，請改用 get_secret）
    return _cache.get(key, DEFAULTS.get(key, ""))


def get_secret(key: str) -> str:
    # 取得加密儲存的設定值的明文
    return _decrypt(get(key))


def is_enabled(key: str) -> bool:
    # 取得布林類設定（telegram_enabled 等）
    return get(key).lower() == "true"


async def save(pool: asyncpg.Pool, data: dict[str, str]) -> None:
    # 寫入 DB 並同步更新記憶體快取
    data = {k: (_encrypt(v) if k in SECRET_KEYS else v) for k, v in data.items()}
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


async def encrypt_legacy_secrets(pool: asyncpg.Pool) -> None:
    # 舊版把 API key 明文存在 DB，啟動時順手加密回寫
    legacy = {
        k: _cache[k] for k in SECRET_KEYS
        if _cache.get(k) and not _cache[k].startswith(_ENC_PREFIX)
    }
    if legacy:
        await save(pool, legacy)
        logger.info("已將明文儲存的設定加密：%s", ", ".join(sorted(legacy)))


def all_public() -> dict[str, str]:
    # 回傳所有設定，api_key 已設定時遮罩為 ****
    result = {**DEFAULTS, **_cache}
    for k in SECRET_KEYS:
        if result.get(k):
            result[k] = "****"
    return result

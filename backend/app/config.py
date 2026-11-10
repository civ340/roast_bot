# 從 .env 讀取環境變數，基礎設施設定（token、DB URL 等）
from pydantic_settings import BaseSettings

# 用戶單次輸入的字數上限（超過直接拒絕，避免有人貼整篇文章來燒 token）
MAX_INPUT_CHARS = 1000
# LLM 回覆的字數上限（硬截斷，確保不會超過各平台單則訊息長度，Discord 是 2000）
MAX_OUTPUT_CHARS = 1500

MIN_SECRET_LENGTH = 16
_PLACEHOLDER_SECRETS = {"changeme", "change-me", "change_me", "secret", "password"}


class Settings(BaseSettings):
    # 資料庫連線字串
    database_url:    str
    api_secret_key:  str
    api_base_url:    str = "http://localhost:8000"

    # Telegram Bot Token（@BotFather 取得）
    telegram_bot_token: str = ""

    # LINE Messaging API（LINE Developers Console 取得）
    line_channel_secret:       str = ""
    line_channel_access_token: str = ""

    # Discord Bot Token（Discord Developer Portal 取得）
    discord_bot_token: str = ""

    # 允許帶 cookie 跨來源呼叫後台 API 的來源（逗號分隔）。
    # 正式環境前後端同源（都走 nginx），不需要 CORS；這只給本機 `npm run dev` 用。
    cors_origins: str = "http://localhost:5173"

    # 單次 LLM 呼叫的總時限（秒）。bot 對 backend 的 HTTP timeout 會是這個值 + 10
    llm_timeout_seconds: int = 55

    # 每位用戶的呼叫頻率上限，0 代表不限制
    rate_limit_per_minute: int = 10
    rate_limit_per_day:    int = 200

    # 資料保留天數，0 代表永久保留
    log_retention_days:     int = 30  # request_logs
    message_retention_days: int = 0   # 對話內容（messages / sessions）

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()


def check_api_secret_key() -> None:
    # API_SECRET_KEY 同時是 bot 對內部端點的共享密鑰，也是後台 LLM API key 的加密金鑰來源，
    # 不能是範例值或太短
    key = settings.api_secret_key.strip()
    if key.lower() in _PLACEHOLDER_SECRETS or len(key) < MIN_SECRET_LENGTH:
        raise RuntimeError(
            f"API_SECRET_KEY 不可為空、不可使用範例值（changeme），且至少要 {MIN_SECRET_LENGTH} 個字元。"
            "可以用這個指令產生：python -c \"import secrets; print(secrets.token_urlsafe(32))\""
        )

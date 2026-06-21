# 從 .env 讀取環境變數，基礎設施設定（token、DB URL 等）
from pydantic_settings import BaseSettings


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

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()

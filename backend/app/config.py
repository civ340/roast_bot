from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Infrastructure
    database_url:    str
    api_secret_key:  str
    api_base_url:    str = "http://localhost:8000"

    # Telegram
    telegram_bot_token: str = ""

    # LINE
    line_channel_secret:       str = ""
    line_channel_access_token: str = ""

    # Discord
    discord_bot_token: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()

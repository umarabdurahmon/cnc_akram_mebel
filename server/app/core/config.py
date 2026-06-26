from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Смотрим .env и ../.env (чтобы работало и из server/, и из корня проекта)
        env_file=[".env", "../.env"],
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str
    bot_token: str = ""
    client_bot_token: str = ""
    miniapp_url: str = ""
    storage_root: str = "./storage"
    shop_tz: str = "Asia/Tashkent"
    # Comma-separated list of allowed CORS origins, e.g. "https://t.me,https://example.com"
    cors_origins: str = ""


settings = Settings()

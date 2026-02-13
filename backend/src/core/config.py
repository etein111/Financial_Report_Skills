from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    app_env: str = Field(default="development", alias="APP_ENV")
    debug: bool = Field(default=True, alias="DEBUG")

    supabase_url: str = Field(default="", alias="SUPABASE_URL")
    supabase_anon_key: str = Field(default="", alias="SUPABASE_ANON_KEY")
    supabase_service_role_key: str = Field(default="", alias="SUPABASE_SERVICE_ROLE_KEY")
    supabase_password_reset_redirect: str = Field(
        default="", alias="SUPABASE_PASSWORD_RESET_REDIRECT"
    )

    session_cookie_name: str = Field(default="access_token", alias="SESSION_COOKIE_NAME")
    session_cookie_max_age: int = Field(default=86400, alias="SESSION_COOKIE_MAX_AGE")
    session_cookie_secure: bool = Field(default=True, alias="SESSION_COOKIE_SECURE")
    session_cookie_samesite: str = Field(default="lax", alias="SESSION_COOKIE_SAMESITE")
    page_size: int = Field(default=15, alias="PAGE_SIZE")
    timezone: str = Field(default="Asia/Shanghai", alias="TIMEZONE")

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


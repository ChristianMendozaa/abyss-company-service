# app/config.py
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Supabase Configuration
    supabase_url: str
    supabase_service_role_key: str

    # JWT / Cookie (aunque aquí usamos Supabase Access Token como cookie)
    jwt_secret: str | None = None  # opcional, por si lo usas después

    # Cookie con el access_token de Supabase
    cookie_name: str = "session"

    # PostgreSQL (Supabase)
    database_url: str

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
class _CachedSettings(Settings):
    pass


@lru_cache()
def get_settings() -> Settings:
    return _CachedSettings()

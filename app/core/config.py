from functools import lru_cache

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App
    app_name: str = "Backend API"
    app_env: str = "development"
    debug: bool = False

    # Server
    host: str = "127.0.0.1"
    port: int = 8080

    # Database
    database_url: str | None = None
    db_echo: bool = True
    db_pool_size: int = 5
    db_max_overflow: int = 10

    # SuperAdmin
    superadmin_email: str = "admin@local.dev"
    superadmin_name: str = "Super"
    superadmin_last_name: str = "Admin"
    superadmin_password: str | None = None

    # Security
    secret_key: str = "your-secret-key-change-this-in-production"
    access_token_expire_minutes: int = 60

    # Supabase Storage
    supabase_url: str | None = None
    supabase_service_role_key: str | None = None
    supabase_storage_bucket: str | None = None

    # CORS — comma-separated string, e.g. "http://localhost:5173,https://app.example.com"
    cors_origins: str = ""

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        if self.app_env == "production":
            if self.secret_key == "your-secret-key-change-this-in-production":
                raise ValueError("SECRET_KEY must be set to a secure value in production")
            if len(self.secret_key) < 32:
                raise ValueError("SECRET_KEY must be at least 32 characters in production")
        return self

    @field_validator("debug", mode="before")
    @classmethod
    def normalize_debug(cls, value: object) -> object:
        if not isinstance(value, str):
            return value

        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on", "debug", "development"}:
            return True
        if normalized in {"0", "false", "no", "off", "release", "production"}:
            return False
        return value

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()

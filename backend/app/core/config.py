"""Application configuration loaded from environment variables / .env file."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration object (12-factor style, env driven)."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Application -----------------------------------------------------
    APP_NAME: str = "DealerHub API"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    API_V1_PREFIX: str = "/api/v1"

    # --- Security --------------------------------------------------------
    SECRET_KEY: str = "dev-secret-key-change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 14
    JWT_ISSUER: str = "dealerhub"

    # --- Database --------------------------------------------------------
    DATABASE_URL: str = "postgresql+asyncpg://dealerhub:dealerhub@localhost:5433/dealerhub"

    # --- Redis / caching -------------------------------------------------
    REDIS_URL: str = "redis://localhost:6380/0"
    CACHE_TTL_SECONDS: int = 60

    # --- CORS ------------------------------------------------------------
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    # --- OpenAI ----------------------------------------------------------
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_TIMEOUT_SECONDS: int = 30
    OPENAI_MAX_TOKENS: int = 600

    # --- SMTP (background e-mail jobs) -----------------------------------
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "noreply@dealerhub.example"
    SMTP_STARTTLS: bool = True

    # --- Background worker ------------------------------------------------
    WORKER_QUEUE_NAME: str = "dealerhub"
    LEAD_REMINDER_LOOKAHEAD_DAYS: int = 3


@lru_cache
def get_settings() -> Settings:
    """Return a cached singleton of the application settings."""
    return Settings()


settings = get_settings()

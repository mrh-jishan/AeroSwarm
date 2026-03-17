"""Application configuration — loaded from environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # ── Database ──────────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://aeroswarm:aeroswarm_dev_secret@localhost:5432/aeroswarm"

    # ── Redis ─────────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379"

    # ── Security ──────────────────────────────────────────────────────────────
    SECRET_KEY: str = "change_me_in_production"
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]
    API_BEARER_TOKEN: str = ""
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 12
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    PASSWORD_RESET_EXPIRE_MINUTES: int = 30
    AUTH_RATE_LIMIT_WINDOW_SECONDS: int = 900
    AUTH_RATE_LIMIT_MAX_ATTEMPTS: int = 10
    ACCESS_COOKIE_NAME: str = "aeroswarm_access"
    REFRESH_COOKIE_NAME: str = "aeroswarm_refresh"
    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: str = "lax"
    RUN_MIGRATIONS_ON_STARTUP: bool = False
    EXPOSE_DEV_TOKENS: bool = False

    # ── LLM ───────────────────────────────────────────────────────────────────
    OPENAI_API_KEY: str = ""
    MANAGER_MODEL: str = "gpt-4o"

    # ── Docker / Infrastructure ───────────────────────────────────────────────
    DOCKER_AGENT_IMAGE: str = "aeroswarm-agent:latest"
    REPO_BASE_PATH: str = "/repos"
    AGENT_PORT_RANGE_START: int = 10000
    AGENT_PORT_RANGE_END: int = 20000
    AGENT_MAX_TTL_SECONDS: int = 3600  # 1 hour hard stop
    JANITOR_COMMAND_TIMEOUT_SECONDS: int = 600


settings = Settings()

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
    CSRF_COOKIE_NAME: str = "aeroswarm_csrf"
    CSRF_HEADER_NAME: str = "X-CSRF-Token"
    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: str = "lax"
    RUN_MIGRATIONS_ON_STARTUP: bool = False
    EXPOSE_DEV_TOKENS: bool = False
    FRONTEND_URL: str = "http://localhost:3000"
    GITHUB_OAUTH_CLIENT_ID: str = ""
    GITHUB_OAUTH_CLIENT_SECRET: str = ""
    GITHUB_OAUTH_REDIRECT_URI: str = "http://localhost:8000/api/vcs/github/oauth/callback"
    GITHUB_OAUTH_STATE_TTL_SECONDS: int = 600
    GITHUB_APP_ID: str = ""
    GITHUB_APP_SLUG: str = ""
    GITHUB_APP_PRIVATE_KEY: str = ""
    GITHUB_APP_STATE_TTL_SECONDS: int = 600
    GITHUB_WEBHOOK_SECRET: str = ""

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
    JOB_POLL_INTERVAL_SECONDS: int = 2
    JOB_MAX_ATTEMPTS: int = 3
    JOB_RETRY_BASE_SECONDS: int = 15
    JOB_LOCK_TIMEOUT_SECONDS: int = 900


settings = Settings()

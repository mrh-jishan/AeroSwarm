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

    # ── LLM ───────────────────────────────────────────────────────────────────
    OPENAI_API_KEY: str = ""
    MANAGER_MODEL: str = "gpt-4o"

    # ── Docker / Infrastructure ───────────────────────────────────────────────
    DOCKER_AGENT_IMAGE: str = "aeroswarm-agent:latest"
    REPO_BASE_PATH: str = "/repos"
    AGENT_PORT_RANGE_START: int = 10000
    AGENT_PORT_RANGE_END: int = 20000
    AGENT_MAX_TTL_SECONDS: int = 3600  # 1 hour hard stop


settings = Settings()

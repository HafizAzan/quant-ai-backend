from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "QuantAI"
    app_env: str = "development"
    api_v1_prefix: str = "/api/v1"
    debug: bool = True

    database_url: str = "postgresql+asyncpg://quantai:quantai@localhost:5432/quantai"
    database_url_sync: str = "postgresql+psycopg://quantai:quantai@localhost:5432/quantai"
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret_key: str = "change-me-to-a-long-random-secret-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 14
    fernet_secret_key: str = ""

    cors_origins: str = "http://localhost:3000"
    bcrypt_rounds: int = 12

    # LLM: auto picks openai → cursor (first key present wins)
    llm_provider: str = "auto"  # auto|openai|cursor
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"
    cursor_api_key: str = ""
    cursor_model: str = "composer-2.5"
    cursor_cwd: str = ""

    celery_broker_url: str = ""
    celery_result_backend: str = ""

    @property
    def celery_broker(self) -> str:
        return self.celery_broker_url or self.redis_url

    @property
    def celery_backend(self) -> str:
        return self.celery_result_backend or self.redis_url

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def resolved_llm_provider(self) -> str | None:
        provider = (self.llm_provider or "auto").strip().lower()
        if provider == "openai":
            return "openai" if self.openai_api_key else None
        if provider == "cursor":
            return "cursor" if self.cursor_api_key else None
        # auto: OpenAI first, then Cursor
        if self.openai_api_key:
            return "openai"
        if self.cursor_api_key:
            return "cursor"
        return None


settings = Settings()

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

    cors_origins: str = "http://localhost:3000"
    bcrypt_rounds: int = 12

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()

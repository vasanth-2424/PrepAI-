from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    app_name: str = "PrepAI"
    app_env: str = "development"
    debug: bool = True

    host: str = "0.0.0.0"
    port: int = 8000

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    database_url: str = "postgresql+psycopg://prepai:prepai@localhost:5432/prepai"

    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # LLM (OpenAI-compatible)
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_base_url: str = "https://api.openai.com/v1"
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"
    llm_max_retries: int = 2

    # Resume upload limits
    max_upload_size_mb: int = 5

    @property
    def cors_origins_list(self) -> list[str]:
        return [
            origin.strip().rstrip("/")
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]

    @property
    def sqlalchemy_database_url(self) -> str:
        url = self.database_url.strip()
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+psycopg://", 1)
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+psycopg://", 1)
        return url

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def llm_api_key(self) -> str:
        return self.openai_api_key or self.groq_api_key

    @property
    def llm_base_url(self) -> str:
        if self.groq_api_key and not self.openai_api_key:
            return "https://api.groq.com/openai/v1"
        return self.openai_base_url

    @property
    def llm_model(self) -> str:
        if self.groq_api_key and not self.openai_api_key:
            return self.groq_model
        return self.openai_model


@lru_cache
def get_settings() -> Settings:
    return Settings()

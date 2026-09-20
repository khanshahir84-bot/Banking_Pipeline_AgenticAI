"""Typed runtime configuration loaded from environment variables only."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration for third-party LLM, identity provider, persistence, and logging."""

    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    llm_timeout_seconds: float = 30.0
    llm_required: bool = False
    auth_mode: str = "development"  # development or jwks
    jwt_secret: str = "change-me-before-production"
    developer_token: str = ""
    jwt_issuer: str = ""
    jwt_audience: str = ""
    jwt_jwks_url: str = ""
    database_path: str = "/tmp/banking_chat.db"
    log_level: str = "INFO"
    max_history_messages: int = 10
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

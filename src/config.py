"""Application configuration using Pydantic settings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # OpenAI Configuration
    openai_api_key: str = Field(..., description="OpenAI API key")
    openai_base_url: str = Field(
        default="https://api.openai.com/v1",
        description="OpenAI base URL (supports OpenRouter, Ollama)",
    )
    openai_model: str = Field(
        default="gpt-4-turbo-preview",
        description="OpenAI model name",
    )
    openai_timeout: int = Field(default=60, description="Request timeout in seconds")
    openai_max_retries: int = Field(default=3, description="Max retry attempts")

    # Database Configuration
    database_url: str = Field(
        default="sqlite+aiosqlite:///./data/qna_agent.db",
        description="SQLite database URL",
    )

    # Application Configuration
    app_host: str = Field(default="0.0.0.0", description="Application host")
    app_port: int = Field(default=8000, description="Application port")
    app_log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level",
    )
    app_reload: bool = Field(
        default=False, description="Enable auto-reload for development"
    )

    # Knowledge Base Configuration
    knowledge_base_dir: str = Field(
        default="./knowledge",
        description="Directory containing knowledge base .txt files",
    )


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings instance."""
    return Settings()  # type: ignore[call-arg]

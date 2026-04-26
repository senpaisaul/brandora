"""Application configuration loaded from .env via pydantic-settings."""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Secrets
    anthropic_api_key: str
    apify_api_token: str

    # Storage
    database_url: str = "sqlite:///./brandora.db"
    image_cache_dir: str = "./cache/images"

    # Model selection — single source of truth
    model_haiku: str = "claude-haiku-4-5-20251001"
    model_opus: str = "claude-opus-4-7"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def image_cache_path(self) -> Path:
        p = Path(self.image_cache_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p


settings = Settings()  # type: ignore[call-arg]
"""
Application settings

All settings come from environment variables (or a `.env` file). See
docs/configuration.md for the full list.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from health_score.basepoint.client import DEFAULT_BASE_URL


class Settings(BaseSettings):
    """Runtime configuration"""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    fss_api_url: str = Field(DEFAULT_BASE_URL, description="BASEPOINT (FSS) API base URL")
    fss_timeout_seconds: float = Field(90, gt=0, description="Timeout for one BASEPOINT request")

    api_keys: str = Field(
        "", description="Comma-separated API keys for the HTTP API; empty means no API key is required"
    )
    log_level: str = Field("INFO", description="Python logging level")

    @property
    def api_key_list(self) -> list[str]:
        return [k.strip() for k in self.api_keys.split(",") if k.strip()]


@lru_cache
def get_settings() -> Settings:
    """Settings loaded once per process"""
    return Settings()

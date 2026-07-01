from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


ProviderMode = Literal["REAL_MODE", "SAMPLE_MODE", "TEST_MODE"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    provider_mode: ProviderMode = "SAMPLE_MODE"
    database_url: str = "postgresql+asyncpg://thriftlens:thriftlens@postgres:5432/thriftlens"
    db_pool_size: int = Field(default=5, ge=1)
    db_max_overflow: int = Field(default=10, ge=0)
    redis_url: str = "redis://redis:6379/0"

    gemini_api_key: str = ""
    serpapi_api_key: str = ""
    serpapi_mcp_base_url: str = "https://mcp.serpapi.com"

    minio_endpoint: str = "minio:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "thriftlens-uploads"
    object_storage_force_path_style: bool = True
    object_storage_secure: bool = False

    max_queued_jobs: int = Field(default=50, ge=1)
    max_active_jobs: int = Field(default=10, ge=1)
    max_upload_mb: int = Field(default=8, ge=1)
    max_text_length: int = Field(default=2000, ge=1)
    live_provider_smoke: bool = False

    def require_real_provider_keys(self) -> list[str]:
        missing: list[str] = []
        if self.provider_mode == "REAL_MODE":
            if not self.gemini_api_key:
                missing.append("GEMINI_API_KEY")
            if not self.serpapi_api_key:
                missing.append("SERPAPI_API_KEY")
        return missing

    def build_serpapi_mcp_url(self) -> str:
        base_url = self.serpapi_mcp_base_url.rstrip("/")
        if not self.serpapi_api_key:
            return f"{base_url}/mcp"
        return f"{base_url}/{self.serpapi_api_key}/mcp"


@lru_cache
def get_settings() -> Settings:
    return Settings()

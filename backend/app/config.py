from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


ProviderMode = Literal["REAL_MODE", "SAMPLE_MODE", "TEST_MODE"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    provider_mode: ProviderMode = "SAMPLE_MODE"
    cors_allowed_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    database_url: str = "postgresql+asyncpg://thriftlens:thriftlens@postgres:5432/thriftlens"
    db_pool_size: int = Field(default=5, ge=1)
    db_max_overflow: int = Field(default=10, ge=0)
    redis_url: str = "redis://redis:6379/0"

    gemini_api_key: str = ""
    google_api_key: str = ""
    google_cloud_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash"
    gemini_extraction_model: str = ""
    gemini_extraction_fallback_model: str = ""
    gemini_extraction_quality_model: str = ""
    gemini_text_safety_model: str = ""
    gemini_repair_model: str = ""
    gemini_ranking_model: str = ""
    gemini_ranking_enabled: bool = False
    serpapi_api_key: str = ""
    serpapi_mcp_base_url: str = "https://mcp.serpapi.com"
    serpapi_max_calls_per_job: int = Field(default=2, ge=1)
    serpapi_timeout_seconds: float = Field(default=60.0, gt=0)
    provider_timeout_seconds: float = Field(default=20.0, gt=0)
    provider_max_retries: int = Field(default=1, ge=0)
    provider_backoff_base_seconds: float = Field(default=2.0, gt=0)
    provider_backoff_max_seconds: float = Field(default=15.0, gt=0)
    provider_jitter_ratio: float = Field(default=0.25, ge=0, le=1)
    circuit_breaker_failure_threshold: int = Field(default=3, ge=1)
    circuit_breaker_window_seconds: int = Field(default=120, ge=1)
    circuit_breaker_cooldown_seconds: int = Field(default=300, ge=1)
    input_gate_min_product_confidence: float = Field(default=0.65, ge=0, le=1)
    input_gate_target_match_confidence: float = Field(default=0.70, ge=0, le=1)
    input_gate_quality_model_confidence: float = Field(default=0.82, ge=0, le=1)
    input_gate_max_products_without_target: int = Field(default=1, ge=1)
    text_safety_model_enabled: bool = False
    text_safety_model_safe_threshold: float = Field(default=0.74, ge=0, le=1)
    text_safety_model_unsafe_threshold: float = Field(default=0.68, ge=0, le=1)
    product_understanding_agent_enabled: bool = False
    product_understanding_model: str = ""
    product_understanding_max_tool_calls: int = Field(default=3, ge=1, le=5)
    extraction_mcp_url: str = ""
    extraction_mcp_host: str = ""
    extraction_mcp_port: int = Field(default=8001, ge=1)
    discovery_mcp_url: str = ""
    discovery_mcp_host: str = ""
    discovery_mcp_port: int = Field(default=8002, ge=1)
    discovery_model: str = ""
    discovery_max_engines: int = Field(default=3, ge=1, le=5)
    discovery_engine_allowlist: str = "google_shopping,google,bing_shopping,ebay,amazon,walmart,home_depot"
    ranking_mcp_url: str = ""
    ranking_mcp_host: str = ""
    ranking_mcp_port: int = Field(default=8003, ge=1)

    minio_endpoint: str = ""
    minio_host: str = ""
    minio_port: int = Field(default=9000, ge=1)
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "thriftlens-uploads"
    object_storage_force_path_style: bool = True
    object_storage_secure: bool = False

    max_queued_jobs: int = Field(default=50, ge=1)
    max_active_jobs: int = Field(default=10, ge=1)
    max_upload_mb: int = Field(default=8, ge=1)
    max_text_length: int = Field(default=2000, ge=1)
    image_retention_seconds: int = Field(default=21600, ge=1)
    image_cleanup_batch_size: int = Field(default=100, ge=1)
    image_cleanup_interval_seconds: int = Field(default=900, ge=60)
    live_provider_smoke: bool = False

    def require_real_provider_keys(self) -> list[str]:
        missing: list[str] = []
        if self.provider_mode == "REAL_MODE":
            if not self.gemini_provider_api_key():
                missing.append("GEMINI_API_KEY or GOOGLE_CLOUD_API_KEY")
            if not self.serpapi_api_key:
                missing.append("SERPAPI_API_KEY")
        return missing

    def gemini_provider_api_key(self) -> str:
        return self.gemini_api_key.strip() or self.google_api_key.strip() or self.google_cloud_api_key.strip()

    def sqlalchemy_database_url(self) -> str:
        url = self.database_url.strip()
        if url.startswith("postgresql+asyncpg://"):
            return url
        if url.startswith("postgresql://"):
            return f"postgresql+asyncpg://{url.split('://', 1)[1]}"
        if url.startswith("postgres://"):
            return f"postgresql+asyncpg://{url.split('://', 1)[1]}"
        return url

    def build_serpapi_mcp_url(self) -> str:
        base_url = self.serpapi_mcp_base_url.rstrip("/")
        if not self.serpapi_api_key:
            return f"{base_url}/mcp"
        return f"{base_url}/{self.serpapi_api_key}/mcp"

    def gemini_extraction_model_name(self) -> str:
        return self.gemini_extraction_model.strip() or self.gemini_model

    def gemini_extraction_fallback_model_name(self) -> str | None:
        fallback = self.gemini_extraction_fallback_model.strip()
        if not fallback or fallback == self.gemini_extraction_model_name():
            return None
        return fallback

    def gemini_extraction_quality_model_name(self) -> str:
        return self.gemini_extraction_quality_model.strip() or self.gemini_extraction_fallback_model_name() or self.gemini_extraction_model_name()

    def gemini_text_safety_model_name(self) -> str:
        return self.gemini_text_safety_model.strip() or self.gemini_extraction_model_name()

    def gemini_repair_model_name(self) -> str:
        return self.gemini_repair_model.strip() or self.gemini_extraction_model_name()

    def gemini_ranking_model_name(self) -> str:
        return self.gemini_ranking_model.strip() or self.gemini_extraction_model_name()

    def product_understanding_model_name(self) -> str:
        return self.product_understanding_model.strip() or self.gemini_extraction_model_name()

    def discovery_model_name(self) -> str:
        return self.discovery_model.strip() or self.gemini_extraction_model_name()

    def discovery_allowed_engines(self) -> list[str]:
        return [engine.strip() for engine in self.discovery_engine_allowlist.split(",") if engine.strip()]

    def extraction_mcp_endpoint(self) -> str:
        return self._http_service_url(
            explicit_url=self.extraction_mcp_url,
            host=self.extraction_mcp_host,
            port=self.extraction_mcp_port,
            fallback_host="extraction-mcp",
            path="/mcp",
        )

    def discovery_mcp_endpoint(self) -> str:
        return self._http_service_url(
            explicit_url=self.discovery_mcp_url,
            host=self.discovery_mcp_host,
            port=self.discovery_mcp_port,
            fallback_host="discovery-mcp",
            path="/mcp",
        )

    def ranking_mcp_endpoint(self) -> str:
        return self._http_service_url(
            explicit_url=self.ranking_mcp_url,
            host=self.ranking_mcp_host,
            port=self.ranking_mcp_port,
            fallback_host="ranking-mcp",
            path="/mcp",
        )

    def object_storage_endpoint(self) -> str:
        endpoint = self.minio_endpoint.strip()
        if endpoint:
            return endpoint.removeprefix("http://").removeprefix("https://")
        host = self.minio_host.strip() or "minio"
        return f"{host}:{self.minio_port}"

    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]

    def _http_service_url(
        self,
        *,
        explicit_url: str,
        host: str,
        port: int,
        fallback_host: str,
        path: str,
    ) -> str:
        url = explicit_url.strip()
        if url:
            return url
        service_host = host.strip() or fallback_host
        normalized_path = path if path.startswith("/") else f"/{path}"
        return f"http://{service_host}:{port}{normalized_path}"


@lru_cache
def get_settings() -> Settings:
    return Settings()

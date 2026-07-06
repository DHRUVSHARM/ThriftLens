from pathlib import Path
from unittest import SkipTest, TestCase


def find_repo_root() -> Path | None:
    for parent in Path(__file__).resolve().parents:
        if (parent / "docker-compose.yml").exists():
            return parent
    return None


ROOT = find_repo_root()


def read(path: str) -> str:
    if ROOT is None:
        raise SkipTest("Repository root is not mounted in this test environment.")
    return (ROOT / path).read_text(encoding="utf-8")


class RuntimeInfrastructureStaticTests(TestCase):
    def test_required_runtime_environment_variables_are_documented(self) -> None:
        env_example = read(".env.example")
        required_names = {
            "PROVIDER_MODE",
            "NEXT_PUBLIC_API_BASE_URL",
            "CORS_ALLOWED_ORIGINS",
            "DATABASE_URL",
            "DB_POOL_SIZE",
            "DB_MAX_OVERFLOW",
            "REDIS_URL",
            "GEMINI_API_KEY",
            "GOOGLE_API_KEY",
            "GOOGLE_CLOUD_API_KEY",
            "GEMINI_EXTRACTION_MODEL",
            "GEMINI_EXTRACTION_FALLBACK_MODEL",
            "GEMINI_EXTRACTION_QUALITY_MODEL",
            "GEMINI_REPAIR_MODEL",
            "GEMINI_RANKING_MODEL",
            "GEMINI_RANKING_ENABLED",
            "SERPAPI_API_KEY",
            "SERPAPI_MCP_BASE_URL",
            "PROVIDER_BACKOFF_BASE_SECONDS",
            "PROVIDER_BACKOFF_MAX_SECONDS",
            "PROVIDER_JITTER_RATIO",
            "CIRCUIT_BREAKER_FAILURE_THRESHOLD",
            "CIRCUIT_BREAKER_WINDOW_SECONDS",
            "CIRCUIT_BREAKER_COOLDOWN_SECONDS",
            "INPUT_GATE_MIN_PRODUCT_CONFIDENCE",
            "INPUT_GATE_TARGET_MATCH_CONFIDENCE",
            "INPUT_GATE_QUALITY_MODEL_CONFIDENCE",
            "INPUT_GATE_MAX_PRODUCTS_WITHOUT_TARGET",
            "PRODUCT_UNDERSTANDING_AGENT_ENABLED",
            "PRODUCT_UNDERSTANDING_MODEL",
            "PRODUCT_UNDERSTANDING_MAX_TOOL_CALLS",
            "EXTRACTION_MCP_URL",
            "EXTRACTION_MCP_HOST",
            "EXTRACTION_MCP_PORT",
            "DISCOVERY_MCP_URL",
            "DISCOVERY_MCP_HOST",
            "DISCOVERY_MCP_PORT",
            "DISCOVERY_MODEL",
            "DISCOVERY_MAX_ENGINES",
            "DISCOVERY_ENGINE_ALLOWLIST",
            "RANKING_MCP_URL",
            "RANKING_MCP_HOST",
            "RANKING_MCP_PORT",
            "MINIO_ENDPOINT",
            "MINIO_HOST",
            "MINIO_PORT",
            "MINIO_ACCESS_KEY",
            "MINIO_SECRET_KEY",
            "MINIO_BUCKET",
            "OBJECT_STORAGE_FORCE_PATH_STYLE",
            "MAX_QUEUED_JOBS",
            "MAX_ACTIVE_JOBS",
            "MAX_UPLOAD_MB",
            "MAX_TEXT_LENGTH",
            "IMAGE_RETENTION_SECONDS",
            "IMAGE_CLEANUP_BATCH_SIZE",
            "IMAGE_CLEANUP_INTERVAL_SECONDS",
            "LIVE_PROVIDER_SMOKE",
        }

        for name in required_names:
            self.assertIn(f"{name}=", env_example)

        self.assertNotIn("sk-", env_example)
        self.assertNotIn("AIza", env_example)

    def test_compose_defines_required_services_and_persistent_storage(self) -> None:
        compose = read("docker-compose.yml")
        required_services = {
            "frontend",
            "api",
            "worker",
            "beat",
            "extraction-mcp",
            "discovery-mcp",
            "ranking-mcp",
            "postgres",
            "redis",
            "minio",
        }

        for service in required_services:
            self.assertIn(f"  {service}:", compose)

        self.assertIn("postgres_data:", compose)
        self.assertIn("minio_data:", compose)
        self.assertIn("minio-init:", compose)
        self.assertIn("mc mb --ignore-existing", compose)
        self.assertIn("celery -A app.worker.celery_app beat", compose)
        self.assertIn("--concurrency=1", compose)
        self.assertIn("--prefetch-multiplier=1", compose)
        self.assertIn("--max-tasks-per-child=10", compose)

    def test_render_blueprint_defines_deployment_services(self) -> None:
        blueprint = read("render.yaml")
        required_services = {
            "thriftlens-web",
            "thriftlens-api",
            "thriftlens-worker",
            "thriftlens-beat",
            "thriftlens-extraction-mcp",
            "thriftlens-discovery-mcp",
            "thriftlens-ranking-mcp",
            "thriftlens-minio",
            "thriftlens-redis",
            "thriftlens-postgres",
        }

        for service in required_services:
            self.assertIn(f"name: {service}", blueprint)

        self.assertIn("type: pserv", blueprint)
        self.assertIn("type: keyvalue", blueprint)
        self.assertIn("dockerfilePath: ./infra/minio/Dockerfile", blueprint)
        self.assertIn("mountPath: /data", blueprint)
        self.assertIn("NEXT_PUBLIC_API_BASE_URL", blueprint)
        self.assertIn("CORS_ALLOWED_ORIGINS", blueprint)
        self.assertIn("healthCheckPath: /api/live", blueprint)
        self.assertNotIn("healthCheckPath: /api/health", blueprint)
        self.assertIn("fromDatabase:", blueprint)
        self.assertIn("connectionString", blueprint)
        self.assertIn("--concurrency=1", blueprint)
        self.assertIn("--prefetch-multiplier=1", blueprint)
        self.assertIn("--max-tasks-per-child=10", blueprint)

    def test_schema_contains_durable_runtime_tables_and_json_artifacts(self) -> None:
        schema = read("backend/app/schema.sql")
        required_tables = {
            "research_jobs",
            "uploaded_images",
            "job_attempts",
            "dependency_health",
        }

        for table in required_tables:
            self.assertIn(f"CREATE TABLE IF NOT EXISTS {table}", schema)

        self.assertIn("product_reference JSONB", schema)
        self.assertIn("partial_brief JSONB", schema)
        self.assertIn("final_brief JSONB", schema)
        self.assertIn("safe_error JSONB", schema)
        self.assertIn("metadata JSONB", schema)
        self.assertIn("object_key TEXT NOT NULL", schema)
        self.assertIn("checksum TEXT", schema)

    def test_redis_is_not_declared_as_durable_product_state(self) -> None:
        schema = read("backend/app/schema.sql").lower()

        self.assertNotIn("redis", schema)
        self.assertIn("research_jobs", schema)
        self.assertIn("final_brief", schema)

    def test_api_and_worker_share_runtime_health_collection(self) -> None:
        health = read("backend/app/health.py")
        api = read("backend/app/main.py")
        worker = read("backend/app/worker.py")

        self.assertIn("async def collect_runtime_health", health)
        self.assertIn('"postgres": False', health)
        self.assertIn('"redis": False', health)
        self.assertIn('"minio": False', health)
        self.assertIn('"geminiConfiguration": True', health)
        self.assertIn('"serpapiConfiguration": True', health)
        self.assertIn("missingProviderKeys", health)

        self.assertIn("@app.get(\"/api/live\")", api)
        self.assertIn('collect_runtime_health("thriftlens-api")', api)
        self.assertIn('collect_runtime_health("thriftlens-worker")', worker)

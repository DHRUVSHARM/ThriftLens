from types import SimpleNamespace

from minio.error import S3Error

from app import storage
from app.config import Settings


def test_render_private_service_endpoints_can_be_derived_from_host_and_port() -> None:
    settings = Settings(
        extraction_mcp_url="",
        extraction_mcp_host="thriftlens-extraction-mcp",
        extraction_mcp_port=8001,
        discovery_mcp_url="",
        discovery_mcp_host="thriftlens-discovery-mcp",
        discovery_mcp_port=8002,
        ranking_mcp_url="",
        ranking_mcp_host="thriftlens-ranking-mcp",
        ranking_mcp_port=8003,
        minio_endpoint="",
        minio_host="thriftlens-minio",
        minio_port=9000,
    )

    assert settings.extraction_mcp_endpoint() == "http://thriftlens-extraction-mcp:8001/mcp"
    assert settings.discovery_mcp_endpoint() == "http://thriftlens-discovery-mcp:8002/mcp"
    assert settings.ranking_mcp_endpoint() == "http://thriftlens-ranking-mcp:8003/mcp"
    assert settings.object_storage_endpoint() == "thriftlens-minio:9000"


def test_explicit_urls_override_render_host_and_port_derivation() -> None:
    settings = Settings(
        extraction_mcp_url="http://custom-extraction:9001/mcp",
        extraction_mcp_host="ignored",
        discovery_mcp_url="http://custom-discovery:9002/mcp",
        discovery_mcp_host="ignored",
        ranking_mcp_url="http://custom-ranking:9003/mcp",
        ranking_mcp_host="ignored",
        minio_endpoint="custom-minio:9443",
        minio_host="ignored",
    )

    assert settings.extraction_mcp_endpoint() == "http://custom-extraction:9001/mcp"
    assert settings.discovery_mcp_endpoint() == "http://custom-discovery:9002/mcp"
    assert settings.ranking_mcp_endpoint() == "http://custom-ranking:9003/mcp"
    assert settings.object_storage_endpoint() == "custom-minio:9443"


def test_render_postgres_url_is_normalized_for_async_sqlalchemy() -> None:
    settings = Settings(database_url="postgresql://user:password@host:5432/thriftlens")

    assert settings.sqlalchemy_database_url() == "postgresql+asyncpg://user:password@host:5432/thriftlens"


def test_minio_bucket_creation_is_idempotent(monkeypatch) -> None:
    class FakeMinio:
        def __init__(self) -> None:
            self.exists = False
            self.make_bucket_calls = 0

        def bucket_exists(self, bucket: str) -> bool:
            assert bucket == "thriftlens-uploads"
            return self.exists

        def make_bucket(self, bucket: str) -> None:
            assert bucket == "thriftlens-uploads"
            self.exists = True
            self.make_bucket_calls += 1

    fake_client = FakeMinio()
    monkeypatch.setattr(storage, "get_settings", lambda: SimpleNamespace(minio_bucket="thriftlens-uploads"))
    monkeypatch.setattr(storage, "create_minio_client", lambda: fake_client)

    storage.ensure_minio_bucket()
    storage.ensure_minio_bucket()

    assert fake_client.make_bucket_calls == 1


def test_minio_bucket_creation_tolerates_concurrent_create(monkeypatch) -> None:
    class FakeMinio:
        def bucket_exists(self, bucket: str) -> bool:
            assert bucket == "thriftlens-uploads"
            return False

        def make_bucket(self, bucket: str) -> None:
            assert bucket == "thriftlens-uploads"
            raise S3Error(
                None,
                "BucketAlreadyOwnedByYou",
                "Bucket was created by another instance.",
                bucket,
                "request-id",
                "host-id",
            )

    monkeypatch.setattr(storage, "get_settings", lambda: SimpleNamespace(minio_bucket="thriftlens-uploads"))
    monkeypatch.setattr(storage, "create_minio_client", lambda: FakeMinio())

    storage.ensure_minio_bucket()

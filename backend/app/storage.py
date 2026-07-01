from minio import Minio

from app.config import get_settings


def create_minio_client() -> Minio:
    settings = get_settings()
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.object_storage_secure,
    )


def check_minio() -> bool:
    settings = get_settings()
    client = create_minio_client()
    return client.bucket_exists(settings.minio_bucket)

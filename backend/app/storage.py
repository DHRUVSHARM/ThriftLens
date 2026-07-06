from minio import Minio
from minio.error import S3Error

from app.config import get_settings


# TODO : sync function called as part of async job with wrappers, investigate reason for this choice and if it can be made better
def create_minio_client() -> Minio:
    settings = get_settings()
    return Minio(
        settings.object_storage_endpoint(),
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.object_storage_secure,
    )


def ensure_minio_bucket() -> None:
    settings = get_settings()
    client = create_minio_client()
    if not client.bucket_exists(settings.minio_bucket):
        try:
            client.make_bucket(settings.minio_bucket)
        except S3Error as exc:
            if exc.code not in {"BucketAlreadyExists", "BucketAlreadyOwnedByYou"}:
                raise


def check_minio() -> bool:
    ensure_minio_bucket()
    return True

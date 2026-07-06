from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
from uuid import uuid4

from app.config import get_settings
from app.storage import create_minio_client


@dataclass(frozen=True)
class StoredImage:
    object_key: str
    checksum: str
    size_bytes: int
    content_type: str


def upload_research_image(*, job_id: str, content: bytes, content_type: str) -> StoredImage:
    settings = get_settings()
    digest = sha256(content).hexdigest()
    extension = {
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/webp": "webp",
    }.get(content_type, "bin")
    object_key = f"uploads/{job_id}/{uuid4()}.{extension}"

    client = create_minio_client()
    client.put_object(
        settings.minio_bucket,
        object_key,
        BytesIO(content),
        length=len(content),
        content_type=content_type,
    )
    return StoredImage(
        object_key=object_key,
        checksum=digest,
        size_bytes=len(content),
        content_type=content_type,
    )


def download_research_image(object_key: str) -> bytes:
    settings = get_settings()
    client = create_minio_client()
    response = client.get_object(settings.minio_bucket, object_key)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


def delete_research_image(object_key: str) -> None:
    settings = get_settings()
    client = create_minio_client()
    client.remove_object(settings.minio_bucket, object_key)

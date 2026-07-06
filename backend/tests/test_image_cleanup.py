from uuid import uuid4

import pytest
from sqlalchemy import text

from app.db import engine, run_schema_migrations
from app.image_cleanup import cleanup_expired_uploaded_images
from app.job_repository import create_research_job
from app.worker import cleanup_expired_images


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def clean_jobs() -> None:
    await engine.dispose()
    await run_schema_migrations()
    async with engine.begin() as connection:
        await connection.execute(text("DELETE FROM job_attempts"))
        await connection.execute(text("DELETE FROM uploaded_images"))
        await connection.execute(text("DELETE FROM research_jobs"))
    yield
    await engine.dispose()


@pytest.mark.anyio
async def test_cleanup_expired_uploaded_images_deletes_object_and_metadata(clean_jobs: None) -> None:
    job_id = await _create_job()
    image_id = await _insert_uploaded_image(job_id=job_id, object_key="uploads/job/expired.png", expired=True)
    deleted_keys: list[str] = []

    result = await cleanup_expired_uploaded_images(limit=10, delete_image=deleted_keys.append)

    assert result == {
        "scanned": 1,
        "deletedObjects": 1,
        "deletedMetadata": 1,
        "failed": 0,
    }
    assert deleted_keys == ["uploads/job/expired.png"]
    assert await _uploaded_image_exists(image_id) is False


@pytest.mark.anyio
async def test_cleanup_expired_uploaded_images_ignores_non_expired_rows(clean_jobs: None) -> None:
    job_id = await _create_job()
    image_id = await _insert_uploaded_image(job_id=job_id, object_key="uploads/job/current.png", expired=False)
    deleted_keys: list[str] = []

    result = await cleanup_expired_uploaded_images(limit=10, delete_image=deleted_keys.append)

    assert result == {
        "scanned": 0,
        "deletedObjects": 0,
        "deletedMetadata": 0,
        "failed": 0,
    }
    assert deleted_keys == []
    assert await _uploaded_image_exists(image_id) is True


@pytest.mark.anyio
async def test_cleanup_expired_uploaded_images_keeps_metadata_when_object_delete_fails(clean_jobs: None) -> None:
    job_id = await _create_job()
    image_id = await _insert_uploaded_image(job_id=job_id, object_key="uploads/job/failed.png", expired=True)

    def fail_delete(_: str) -> None:
        raise RuntimeError("storage temporarily unavailable")

    result = await cleanup_expired_uploaded_images(limit=10, delete_image=fail_delete)

    assert result == {
        "scanned": 1,
        "deletedObjects": 0,
        "deletedMetadata": 0,
        "failed": 1,
    }
    assert await _uploaded_image_exists(image_id) is True


def test_cleanup_expired_images_celery_task_returns_cleanup_counts(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_cleanup(*, limit: int) -> dict:
        return {
            "scanned": 2,
            "deletedObjects": 2,
            "deletedMetadata": 2,
            "failed": 0,
            "limit": limit,
        }

    monkeypatch.setattr("app.worker.cleanup_expired_uploaded_images", fake_cleanup)

    result = cleanup_expired_images.run()

    assert result["scanned"] == 2
    assert result["deletedObjects"] == 2
    assert result["deletedMetadata"] == 2
    assert result["failed"] == 0
    assert result["limit"] >= 1


async def _create_job() -> str:
    job_id = str(uuid4())
    await create_research_job(
        job_id=job_id,
        provider_mode="SAMPLE_MODE",
        input_type="image",
        request_payload={"inputType": "image"},
        progress_message="Research queued.",
    )
    return job_id


async def _insert_uploaded_image(*, job_id: str, object_key: str, expired: bool) -> str:
    offset_seconds = -60 if expired else 60
    async with engine.begin() as connection:
        result = await connection.execute(
            text(
                """
                INSERT INTO uploaded_images (
                    job_id,
                    object_key,
                    content_type,
                    size_bytes,
                    checksum,
                    expires_at
                )
                VALUES (
                    :job_id,
                    :object_key,
                    'image/png',
                    12,
                    'checksum',
                    NOW() + (:offset_seconds * INTERVAL '1 second')
                )
                RETURNING id
                """
            ),
            {
                "job_id": job_id,
                "object_key": object_key,
                "offset_seconds": offset_seconds,
            },
        )
        return str(result.scalar_one())


async def _uploaded_image_exists(image_id: str) -> bool:
    async with engine.connect() as connection:
        result = await connection.execute(
            text("SELECT COUNT(*) FROM uploaded_images WHERE id = :image_id"),
            {"image_id": image_id},
        )
        return int(result.scalar_one()) == 1

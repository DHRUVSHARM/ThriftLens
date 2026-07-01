import json
from typing import Any

from sqlalchemy import text

from app.db import engine


ACTIVE_STATUSES = ("queued", "running")


def _decode_json(value: Any) -> Any:
    if value is None or isinstance(value, (dict, list)):
        return value
    return json.loads(value)


def _job_from_row(row: Any) -> dict[str, Any]:
    mapping = row._mapping
    return {
        "id": str(mapping["id"]),
        "status": mapping["status"],
        "provider_mode": mapping["provider_mode"],
        "input_type": mapping["input_type"],
        "progress_message": mapping["progress_message"],
        "product_reference": _decode_json(mapping["product_reference"]),
        "partial_brief": _decode_json(mapping["partial_brief"]),
        "final_brief": _decode_json(mapping["final_brief"]),
        "retryable": mapping["retryable"],
        "safe_error": _decode_json(mapping["safe_error"]),
    }


async def count_jobs_with_statuses(statuses: tuple[str, ...]) -> int:
    placeholders = ", ".join(f":status_{index}" for index, _ in enumerate(statuses))
    params = {f"status_{index}": value for index, value in enumerate(statuses)}
    async with engine.connect() as connection:
        result = await connection.execute(
            text(f"SELECT COUNT(*) FROM research_jobs WHERE status IN ({placeholders})"),
            params,
        )
        return int(result.scalar_one())


async def create_research_job(
    *,
    job_id: str,
    provider_mode: str,
    input_type: str,
    request_payload: dict[str, Any],
    progress_message: str,
) -> dict[str, Any]:
    async with engine.begin() as connection:
        result = await connection.execute(
            text(
                """
                INSERT INTO research_jobs (
                    id,
                    status,
                    provider_mode,
                    input_type,
                    request_payload,
                    progress_message,
                    expires_at
                )
                VALUES (
                    :job_id,
                    'queued',
                    :provider_mode,
                    :input_type,
                    CAST(:request_payload AS JSONB),
                    :progress_message,
                    NOW() + INTERVAL '2 hours'
                )
                RETURNING *
                """
            ),
            {
                "job_id": job_id,
                "provider_mode": provider_mode,
                "input_type": input_type,
                "request_payload": json.dumps(request_payload),
                "progress_message": progress_message,
            },
        )
        return _job_from_row(result.one())


async def create_uploaded_image(
    *,
    job_id: str,
    object_key: str,
    content_type: str,
    size_bytes: int,
    checksum: str,
) -> None:
    async with engine.begin() as connection:
        await connection.execute(
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
                    :content_type,
                    :size_bytes,
                    :checksum,
                    NOW() + INTERVAL '2 hours'
                )
                """
            ),
            {
                "job_id": job_id,
                "object_key": object_key,
                "content_type": content_type,
                "size_bytes": size_bytes,
                "checksum": checksum,
            },
        )


async def get_research_job(job_id: str) -> dict[str, Any] | None:
    async with engine.connect() as connection:
        result = await connection.execute(
            text(
                """
                SELECT *
                FROM research_jobs
                WHERE id = :job_id
                """
            ),
            {"job_id": job_id},
        )
        row = result.one_or_none()
        if row is None:
            return None
        return _job_from_row(row)


async def mark_job_failed(job_id: str, *, code: str, message: str, retryable: bool) -> None:
    safe_error = {"code": code, "message": message, "retryable": retryable}
    async with engine.begin() as connection:
        await connection.execute(
            text(
                """
                UPDATE research_jobs
                SET
                    status = 'failed',
                    safe_error = CAST(:safe_error AS JSONB),
                    retryable = :retryable,
                    progress_message = :message,
                    updated_at = NOW()
                WHERE id = :job_id
                """
            ),
            {
                "job_id": job_id,
                "safe_error": json.dumps(safe_error),
                "retryable": retryable,
                "message": message,
            },
        )


async def mark_job_queued_for_retry(job_id: str) -> dict[str, Any]:
    async with engine.begin() as connection:
        result = await connection.execute(
            text(
                """
                UPDATE research_jobs
                SET
                    status = 'queued',
                    safe_error = NULL,
                    retryable = FALSE,
                    progress_message = 'Retry queued.',
                    updated_at = NOW()
                WHERE id = :job_id
                RETURNING *
                """
            ),
            {"job_id": job_id},
        )
        return _job_from_row(result.one())


async def mark_sample_job_completed(job_id: str) -> dict[str, Any] | None:
    final_brief = {
        "mode": "sample",
        "label": "Sample/static result",
        "summary": "This placeholder confirms the gateway, queue, and worker path. Live product research is implemented in the provider slices.",
        "matches": [],
        "sourceNote": "No live provider was called in SAMPLE_MODE.",
    }
    async with engine.begin() as connection:
        result = await connection.execute(
            text(
                """
                UPDATE research_jobs
                SET
                    status = 'completed',
                    progress_message = 'Sample research complete.',
                    final_brief = CAST(:final_brief AS JSONB),
                    retryable = FALSE,
                    updated_at = NOW()
                WHERE id = :job_id AND provider_mode = 'SAMPLE_MODE'
                RETURNING *
                """
            ),
            {"job_id": job_id, "final_brief": json.dumps(final_brief)},
        )
        row = result.one_or_none()
        if row is None:
            return None
        return _job_from_row(row)

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import text

from app.db import engine


ACTIVE_STATUSES = ("queued", "running")
DEPENDENCY_HEALTH_COLUMNS = (
    "dependency, state, recent_failure_count, recent_success_count, opened_at, cooldown_until, updated_at"
)


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
        "request_payload": _decode_json(mapping["request_payload"]),
        "progress_message": mapping["progress_message"],
        "product_reference": _decode_json(mapping["product_reference"]),
        "partial_brief": _decode_json(mapping["partial_brief"]),
        "final_brief": _decode_json(mapping["final_brief"]),
        "retryable": mapping["retryable"],
        "safe_error": _decode_json(mapping["safe_error"]),
    }


def _dependency_health_from_row(row: Any) -> dict[str, Any]:
    mapping = row._mapping
    return {
        "dependency": mapping["dependency"],
        "state": mapping["state"],
        "recent_failure_count": mapping["recent_failure_count"],
        "recent_success_count": mapping["recent_success_count"],
        "opened_at": mapping["opened_at"],
        "cooldown_until": mapping["cooldown_until"],
        "updated_at": mapping["updated_at"],
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


async def get_uploaded_images(job_id: str) -> list[dict[str, Any]]:
    async with engine.connect() as connection:
        result = await connection.execute(
            text(
                """
                SELECT object_key, content_type, size_bytes, checksum, expires_at
                FROM uploaded_images
                WHERE job_id = :job_id
                ORDER BY created_at ASC
                """
            ),
            {"job_id": job_id},
        )
        return [
            {
                "object_key": row._mapping["object_key"],
                "content_type": row._mapping["content_type"],
                "size_bytes": row._mapping["size_bytes"],
                "checksum": row._mapping["checksum"],
                "expires_at": row._mapping["expires_at"],
            }
            for row in result
        ]


async def record_job_attempt(
    *,
    job_id: str,
    stage: str,
    dependency: str,
    attempt: int,
    error_code: str | None = None,
    retryable: bool = False,
    metadata: dict[str, Any] | None = None,
) -> None:
    async with engine.begin() as connection:
        await connection.execute(
            text(
                """
                INSERT INTO job_attempts (
                    job_id,
                    stage,
                    dependency,
                    attempt,
                    error_code,
                    retryable,
                    metadata,
                    finished_at
                )
                VALUES (
                    :job_id,
                    :stage,
                    :dependency,
                    :attempt,
                    :error_code,
                    :retryable,
                    CAST(:metadata AS JSONB),
                    NOW()
                )
                """
            ),
            {
                "job_id": job_id,
                "stage": stage,
                "dependency": dependency,
                "attempt": attempt,
                "error_code": error_code,
                "retryable": retryable,
                "metadata": json.dumps(metadata or {}),
            },
        )


async def count_job_attempts(job_id: str) -> int:
    async with engine.connect() as connection:
        result = await connection.execute(
            text("SELECT COUNT(*) FROM job_attempts WHERE job_id = :job_id"),
            {"job_id": job_id},
        )
        return int(result.scalar_one())


async def get_job_attempts(job_id: str) -> list[dict[str, Any]]:
    async with engine.connect() as connection:
        result = await connection.execute(
            text(
                """
                SELECT stage, dependency, attempt, error_code, retryable, metadata, started_at, finished_at
                FROM job_attempts
                WHERE job_id = :job_id
                ORDER BY started_at ASC, id ASC
                """
            ),
            {"job_id": job_id},
        )
        return [
            {
                "stage": row._mapping["stage"],
                "dependency": row._mapping["dependency"],
                "attempt": row._mapping["attempt"],
                "error_code": row._mapping["error_code"],
                "retryable": row._mapping["retryable"],
                "metadata": _decode_json(row._mapping["metadata"]) or {},
                "started_at": row._mapping["started_at"],
                "finished_at": row._mapping["finished_at"],
            }
            for row in result
        ]


async def update_dependency_health(
    *,
    dependency: str,
    state: str,
    failure: bool = False,
) -> None:
    async with engine.begin() as connection:
        await connection.execute(
            text(
                """
                INSERT INTO dependency_health (
                    dependency,
                    state,
                    recent_failure_count,
                    recent_success_count,
                    updated_at
                )
                VALUES (
                    :dependency,
                    :state,
                    :failure_count,
                    :success_count,
                    NOW()
                )
                ON CONFLICT (dependency) DO UPDATE
                SET
                    state = EXCLUDED.state,
                    recent_failure_count = dependency_health.recent_failure_count + EXCLUDED.recent_failure_count,
                    recent_success_count = dependency_health.recent_success_count + EXCLUDED.recent_success_count,
                    updated_at = NOW()
                """
            ),
            {
                "dependency": dependency,
                "state": state,
                "failure_count": 1 if failure else 0,
                "success_count": 0 if failure else 1,
            },
        )


async def get_dependency_health(dependency: str) -> dict[str, Any] | None:
    async with engine.connect() as connection:
        result = await connection.execute(
            text(
                f"""
                SELECT {DEPENDENCY_HEALTH_COLUMNS}
                FROM dependency_health
                WHERE dependency = :dependency
                """
            ),
            {"dependency": dependency},
        )
        row = result.one_or_none()
        if row is None:
            return None
        return _dependency_health_from_row(row)


async def mark_dependency_circuit_half_open(dependency: str) -> None:
    async with engine.begin() as connection:
        await connection.execute(
            text(
                """
                INSERT INTO dependency_health (
                    dependency,
                    state,
                    recent_failure_count,
                    recent_success_count,
                    updated_at
                )
                VALUES (
                    :dependency,
                    'half_open',
                    0,
                    0,
                    NOW()
                )
                ON CONFLICT (dependency) DO UPDATE
                SET
                    state = 'half_open',
                    updated_at = NOW()
                """
            ),
            {"dependency": dependency},
        )


async def record_dependency_circuit_success(dependency: str) -> None:
    async with engine.begin() as connection:
        await connection.execute(
            text(
                """
                INSERT INTO dependency_health (
                    dependency,
                    state,
                    recent_failure_count,
                    recent_success_count,
                    opened_at,
                    cooldown_until,
                    updated_at
                )
                VALUES (
                    :dependency,
                    'healthy',
                    0,
                    1,
                    NULL,
                    NULL,
                    NOW()
                )
                ON CONFLICT (dependency) DO UPDATE
                SET
                    state = 'healthy',
                    recent_failure_count = 0,
                    recent_success_count = dependency_health.recent_success_count + 1,
                    opened_at = NULL,
                    cooldown_until = NULL,
                    updated_at = NOW()
                """
            ),
            {"dependency": dependency},
        )


async def record_dependency_circuit_failure(
    dependency: str,
    *,
    failure_threshold: int,
    window_seconds: int,
    cooldown_seconds: int,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(seconds=window_seconds)
    cooldown_until = now + timedelta(seconds=cooldown_seconds)

    async with engine.begin() as connection:
        result = await connection.execute(
            text(
                f"""
                SELECT {DEPENDENCY_HEALTH_COLUMNS}
                FROM dependency_health
                WHERE dependency = :dependency
                FOR UPDATE
                """
            ),
            {"dependency": dependency},
        )
        row = result.one_or_none()
        if row is None:
            previous_count = 0
            updated_at = None
        else:
            mapping = row._mapping
            previous_count = int(mapping["recent_failure_count"])
            updated_at = mapping["updated_at"]

        stale_window = updated_at is None or updated_at < window_start
        failure_count = 1 if stale_window else previous_count + 1
        state = "open" if failure_count >= failure_threshold else "degraded"
        opened_at = now if state == "open" else None
        circuit_cooldown_until = cooldown_until if state == "open" else None

        await connection.execute(
            text(
                """
                INSERT INTO dependency_health (
                    dependency,
                    state,
                    recent_failure_count,
                    recent_success_count,
                    opened_at,
                    cooldown_until,
                    updated_at
                )
                VALUES (
                    :dependency,
                    :state,
                    :failure_count,
                    0,
                    :opened_at,
                    :cooldown_until,
                    :updated_at
                )
                ON CONFLICT (dependency) DO UPDATE
                SET
                    state = EXCLUDED.state,
                    recent_failure_count = EXCLUDED.recent_failure_count,
                    recent_success_count = 0,
                    opened_at = EXCLUDED.opened_at,
                    cooldown_until = EXCLUDED.cooldown_until,
                    updated_at = EXCLUDED.updated_at
                """
            ),
            {
                "dependency": dependency,
                "state": state,
                "failure_count": failure_count,
                "opened_at": opened_at,
                "cooldown_until": circuit_cooldown_until,
                "updated_at": now,
            },
        )

    return {
        "dependency": dependency,
        "state": state,
        "recent_failure_count": failure_count,
        "recent_success_count": 0,
        "opened_at": opened_at,
        "cooldown_until": circuit_cooldown_until,
        "updated_at": now,
    }


async def update_job_stage(job_id: str, *, status: str, progress_message: str) -> None:
    async with engine.begin() as connection:
        await connection.execute(
            text(
                """
                UPDATE research_jobs
                SET
                    status = :status,
                    progress_message = :progress_message,
                    updated_at = NOW()
                WHERE id = :job_id
                """
            ),
            {
                "job_id": job_id,
                "status": status,
                "progress_message": progress_message,
            },
        )


async def store_product_reference(
    job_id: str,
    *,
    product_reference: dict[str, Any],
    progress_message: str,
) -> None:
    async with engine.begin() as connection:
        await connection.execute(
            text(
                """
                UPDATE research_jobs
                SET
                    product_reference = CAST(:product_reference AS JSONB),
                    progress_message = :progress_message,
                    updated_at = NOW()
                WHERE id = :job_id
                """
            ),
            {
                "job_id": job_id,
                "product_reference": json.dumps(product_reference),
                "progress_message": progress_message,
            },
        )


async def store_partial_brief(
    job_id: str,
    *,
    partial_brief: dict[str, Any],
    status: str,
    progress_message: str,
    retryable: bool,
) -> None:
    async with engine.begin() as connection:
        await connection.execute(
            text(
                """
                UPDATE research_jobs
                SET
                    status = :status,
                    partial_brief = CAST(:partial_brief AS JSONB),
                    retryable = :retryable,
                    progress_message = :progress_message,
                    updated_at = NOW()
                WHERE id = :job_id
                """
            ),
            {
                "job_id": job_id,
                "partial_brief": json.dumps(partial_brief),
                "status": status,
                "retryable": retryable,
                "progress_message": progress_message,
            },
        )


async def store_final_brief(
    job_id: str,
    *,
    final_brief: dict[str, Any],
    status: str,
    progress_message: str,
) -> dict[str, Any] | None:
    async with engine.begin() as connection:
        result = await connection.execute(
            text(
                """
                UPDATE research_jobs
                SET
                    status = :status,
                    progress_message = :progress_message,
                    final_brief = CAST(:final_brief AS JSONB),
                    retryable = FALSE,
                    safe_error = NULL,
                    updated_at = NOW()
                WHERE id = :job_id
                RETURNING *
                """
            ),
            {
                "job_id": job_id,
                "final_brief": json.dumps(final_brief),
                "status": status,
                "progress_message": progress_message,
            },
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


async def mark_job_needs_refinement(job_id: str, *, code: str, message: str) -> None:
    safe_error = {"code": code, "message": message, "retryable": False}
    async with engine.begin() as connection:
        await connection.execute(
            text(
                """
                UPDATE research_jobs
                SET
                    status = 'needs_refinement',
                    safe_error = CAST(:safe_error AS JSONB),
                    retryable = FALSE,
                    progress_message = :message,
                    updated_at = NOW()
                WHERE id = :job_id
                """
            ),
            {
                "job_id": job_id,
                "safe_error": json.dumps(safe_error),
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

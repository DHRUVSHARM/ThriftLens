import asyncio
import json
from typing import Any
from uuid import UUID, uuid4

from fastapi import HTTPException, UploadFile, status
from pydantic import ValidationError

from app.config import Settings, get_settings
from app.job_repository import (
    ACTIVE_STATUSES,
    count_jobs_with_statuses,
    create_research_job,
    create_uploaded_image,
    get_research_job,
    mark_job_failed,
    mark_job_queued_for_retry,
)
from app.object_storage import upload_research_image
from app.schemas import CreateResearchJobInput, ResearchJobResponse, SafeError

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
QUEUE_UNAVAILABLE_DETAIL = {
    "code": "queue_unavailable",
    "message": "Research queue is temporarily unavailable. Try again shortly.",
}


def map_job_response(job: dict[str, Any]) -> ResearchJobResponse:
    safe_error = None
    if job["safe_error"]:
        safe_error = SafeError(**job["safe_error"])
    return ResearchJobResponse(
        jobId=job["id"],
        status=job["status"],
        progressMessage=job["progress_message"],
        retryable=job["retryable"],
        providerMode=job["provider_mode"],
        safeError=safe_error,
        partialBrief=job["partial_brief"],
        finalBrief=job["final_brief"],
    )


def parse_preferences(raw_value: Any) -> dict[str, Any]:
    if raw_value in (None, ""):
        return {}
    if isinstance(raw_value, dict):
        return raw_value
    if isinstance(raw_value, str):
        try:
            value = json.loads(raw_value)
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="researchPreferences must be valid JSON.",
            ) from exc
        if not isinstance(value, dict):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="researchPreferences must be an object.",
            )
        return value
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail="researchPreferences must be an object.",
    )


def build_create_input(payload: dict[str, Any]) -> CreateResearchJobInput:
    try:
        return CreateResearchJobInput.model_validate(payload)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=exc.errors(),
        ) from exc


def assert_real_mode_configured(settings: Settings) -> None:
    missing = settings.require_real_provider_keys()
    if missing:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "provider_configuration_missing",
                "message": "Live research is unavailable until required provider keys are configured.",
                "missing": missing,
            },
        )


async def assert_capacity_available(settings: Settings) -> None:
    active_count = await count_jobs_with_statuses(ACTIVE_STATUSES)
    queued_count = await count_jobs_with_statuses(("queued",))
    if active_count >= settings.max_active_jobs or queued_count >= settings.max_queued_jobs:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "research_overloaded",
                "message": "Research is temporarily busy. Try again shortly.",
            },
        )


def assert_valid_text_input(create_input: CreateResearchJobInput, settings: Settings) -> str:
    text = (create_input.text_description or "").strip()
    if not text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="textDescription is required for text research.",
        )
    if len(text) > settings.max_text_length:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"textDescription must be {settings.max_text_length} characters or less.",
        )
    return text


def normalized_optional_text(value: str | None, *, max_length: int, field_name: str) -> str | None:
    text = (value or "").strip()
    if not text:
        return None
    if len(text) > max_length:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"{field_name} must be {max_length} characters or less.",
        )
    return text


async def read_valid_image(file: UploadFile | None, settings: Settings) -> bytes:
    if file is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="image file is required for image research.",
        )
    content_type = file.content_type or ""
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Unsupported image type. Use JPEG, PNG, or WebP.",
        )
    content = await file.read()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if not content:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Uploaded image is empty.",
        )
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"Uploaded image must be {settings.max_upload_mb}MB or smaller.",
        )
    return content


def enqueue_research_job(job_id: str) -> None:
    from app.worker import process_research_job

    process_research_job.delay(job_id)


async def enqueue_or_mark_failed(job_id: str) -> None:
    try:
        enqueue_research_job(job_id)
    except Exception as exc:
        await mark_job_failed(
            job_id,
            code=QUEUE_UNAVAILABLE_DETAIL["code"],
            message=QUEUE_UNAVAILABLE_DETAIL["message"],
            retryable=True,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=QUEUE_UNAVAILABLE_DETAIL,
        ) from exc


async def create_gateway_job(
    *,
    create_input: CreateResearchJobInput,
    image_file: UploadFile | None = None,
) -> ResearchJobResponse:
    settings = get_settings()
    assert_real_mode_configured(settings)
    await assert_capacity_available(settings)

    job_id = str(uuid4())
    request_payload = create_input.model_dump(by_alias=True)
    progress_message = "Research queued."

    if create_input.input_type == "text":
        request_payload["textDescription"] = assert_valid_text_input(create_input, settings)
        request_payload.pop("targetDescription", None)
    elif create_input.input_type == "image":
        target_description = normalized_optional_text(
            create_input.target_description,
            max_length=settings.max_text_length,
            field_name="targetDescription",
        )
        if target_description:
            request_payload["targetDescription"] = target_description
        else:
            request_payload.pop("targetDescription", None)
        image_content = await read_valid_image(image_file, settings)
        try:
            stored_image = await asyncio.to_thread(
                upload_research_image,
                job_id=job_id,
                content=image_content,
                content_type=image_file.content_type or "",
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "code": "image_storage_unavailable",
                    "message": "Image storage is temporarily unavailable. Try again shortly.",
                },
            ) from exc
        request_payload["image"] = {
            "contentType": stored_image.content_type,
            "sizeBytes": stored_image.size_bytes,
            "checksum": stored_image.checksum,
        }
    else:  # pragma: no cover - pydantic constrains this
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Unsupported inputType.")

    try:
        job = await create_research_job(
            job_id=job_id,
            provider_mode=settings.provider_mode,
            input_type=create_input.input_type,
            request_payload=request_payload,
            progress_message=progress_message,
        )
        if create_input.input_type == "image":
            await create_uploaded_image(
                job_id=job_id,
                object_key=stored_image.object_key,
                content_type=stored_image.content_type,
                size_bytes=stored_image.size_bytes,
                checksum=stored_image.checksum,
                retention_seconds=settings.image_retention_seconds,
            )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "job_store_unavailable",
                "message": "Research job storage is temporarily unavailable. Try again shortly.",
            },
        ) from exc

    await enqueue_or_mark_failed(job_id)

    return map_job_response(job)


async def get_gateway_job(job_id: str) -> ResearchJobResponse:
    try:
        UUID(job_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Research job not found.") from exc

    job = await get_research_job(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Research job not found.")
    return map_job_response(job)


async def retry_gateway_job(job_id: str) -> ResearchJobResponse:
    job = await get_research_job(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Research job not found.")
    if not job["retryable"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "job_not_retryable",
                "message": "This research job cannot be retried.",
            },
        )
    retried_job = await mark_job_queued_for_retry(job_id)
    await enqueue_or_mark_failed(job_id)
    return map_job_response(retried_job)

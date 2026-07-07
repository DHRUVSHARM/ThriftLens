import logging
from concurrent.futures import TimeoutError as FutureTimeoutError

from celery import Celery

from app.agent.runner import run_agent_job
from app.async_runtime import run_async
from app.config import get_settings
from app.health import collect_runtime_health
from app.image_cleanup import cleanup_expired_uploaded_images
from app.job_repository import mark_job_failed
from app.logging_config import configure_secret_redaction_logging

configure_secret_redaction_logging()
settings = get_settings()
logger = logging.getLogger(__name__)

TASK_TIME_LIMIT_SECONDS = 300
TASK_SOFT_TIME_LIMIT_SECONDS = 240
WORKER_RUN_TIMEOUT_SECONDS = TASK_SOFT_TIME_LIMIT_SECONDS - 10

celery_app = Celery(
    "thriftlens",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_track_started=True,
    task_time_limit=TASK_TIME_LIMIT_SECONDS,
    task_soft_time_limit=TASK_SOFT_TIME_LIMIT_SECONDS,
    beat_schedule={
        "cleanup-expired-images": {
            "task": "cleanup_expired_images",
            "schedule": settings.image_cleanup_interval_seconds,
        }
    },
)


@celery_app.task(name="healthcheck")
def healthcheck() -> dict:
    return run_async(collect_runtime_health("thriftlens-worker"))


@celery_app.task(name="cleanup_expired_images")
def cleanup_expired_images() -> dict:
    return run_async(cleanup_expired_uploaded_images(limit=settings.image_cleanup_batch_size))


@celery_app.task(name="process_research_job")
def process_research_job(job_id: str) -> dict:
    try:
        result = run_async(run_agent_job(job_id), timeout=WORKER_RUN_TIMEOUT_SECONDS)
        return result.model_dump(by_alias=True)
    except FutureTimeoutError:
        logger.warning("Research worker timed out for job %s", job_id)
        run_async(
            mark_job_failed(
                job_id,
                code="worker_task_timeout",
                message="Research took too long. Try again with clearer product evidence.",
                retryable=True,
            )
        )
        return {"jobId": job_id, "status": "failed"}
    except Exception:
        logger.exception("Research worker failed unexpectedly for job %s", job_id)
        run_async(
            mark_job_failed(
                job_id,
                code="worker_task_failed",
                message="Research worker failed unexpectedly. Try again.",
                retryable=True,
            )
        )
        return {"jobId": job_id, "status": "failed"}

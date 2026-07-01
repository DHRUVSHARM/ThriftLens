from celery import Celery

from app.async_runtime import run_async
from app.config import get_settings
from app.health import collect_runtime_health
from app.job_repository import mark_sample_job_completed

settings = get_settings()

celery_app = Celery(
    "thriftlens",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_track_started=True,
    task_time_limit=300,
    task_soft_time_limit=240,
)


@celery_app.task(name="healthcheck")
def healthcheck() -> dict:
    return run_async(collect_runtime_health("thriftlens-worker"))


@celery_app.task(name="process_research_job")
def process_research_job(job_id: str) -> dict:
    completed_job = run_async(mark_sample_job_completed(job_id))
    if completed_job is None:
        return {"jobId": job_id, "status": "queued"}
    return {"jobId": job_id, "status": completed_job["status"]}

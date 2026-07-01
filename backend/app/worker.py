from celery import Celery

from app.async_runtime import run_async
from app.config import get_settings
from app.health import collect_runtime_health
from app.workflow import run_research_workflow

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
    result = run_async(run_research_workflow(job_id))
    return result.model_dump(by_alias=True)

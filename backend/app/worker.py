import asyncio

from celery import Celery

from app.config import get_settings
from app.health import collect_runtime_health

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
    return asyncio.run(collect_runtime_health("thriftlens-worker"))

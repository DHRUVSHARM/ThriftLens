from collections.abc import Awaitable, Callable

from app.config import get_settings
from app.db import check_postgres
from app.redis_client import check_redis
from app.storage import check_minio

AsyncCheck = Callable[[], Awaitable[bool]]


async def collect_runtime_health(service_name: str) -> dict:
    settings = get_settings()
    checks: dict[str, bool] = {
        "postgres": False,
        "redis": False,
        "minio": False,
        "geminiConfiguration": True,
        "serpapiConfiguration": True,
    }
    errors: dict[str, str] = {}

    for name, check in (
        ("postgres", check_postgres),
        ("redis", check_redis),
    ):
        try:
            checks[name] = await check()
        except Exception as exc:  # pragma: no cover - dependency errors vary by runtime
            errors[name] = exc.__class__.__name__

    try:
        checks["minio"] = check_minio()
    except Exception as exc:  # pragma: no cover - dependency errors vary by runtime
        errors["minio"] = exc.__class__.__name__

    missing_provider_keys = settings.require_real_provider_keys()
    if "GEMINI_API_KEY" in missing_provider_keys:
        checks["geminiConfiguration"] = False
    if "SERPAPI_API_KEY" in missing_provider_keys:
        checks["serpapiConfiguration"] = False

    status = "ok" if all(checks.values()) else "degraded"
    return {
        "service": service_name,
        "status": status,
        "providerMode": settings.provider_mode,
        "checks": checks,
        "missingProviderKeys": missing_provider_keys,
        "errors": errors,
    }

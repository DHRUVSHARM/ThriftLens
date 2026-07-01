from redis.asyncio import Redis

from app.config import get_settings


def create_redis_client() -> Redis:
    settings = get_settings()
    return Redis.from_url(settings.redis_url)


async def check_redis() -> bool:
    client = create_redis_client()
    try:
        return bool(await client.ping())
    finally:
        await client.aclose()

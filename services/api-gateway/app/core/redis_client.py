import redis.asyncio as redis_lib

_redis: redis_lib.Redis | None = None


async def start_redis(redis_url: str) -> None:
    global _redis
    _redis = redis_lib.from_url(redis_url, decode_responses=True)


async def stop_redis() -> None:
    if _redis:
        await _redis.aclose()


def get_redis() -> redis_lib.Redis:
    return _redis

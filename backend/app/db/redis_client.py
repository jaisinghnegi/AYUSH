import asyncio
from dataclasses import dataclass
from typing import Optional

import redis.asyncio as redis

from app import config


@dataclass
class RedisStatus:
    connected: bool
    server_info: Optional[str] = None
    error: Optional[str] = None


_redis_client: Optional[redis.Redis] = None
_redis_lock = asyncio.Lock()


async def _create_client() -> redis.Redis:
    redis_url = config.REDIS_URL
    print(f"🔗 Connecting to Redis: {redis_url}")
    client = redis.from_url(redis_url, decode_responses=True)
    print("✅ Redis client initialized")
    return client


async def get_instance() -> redis.Redis:
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    async with _redis_lock:
        if _redis_client is None:
            _redis_client = await _create_client()
        return _redis_client


async def init_redis() -> None:
    await get_instance()


async def health_check(client: redis.Redis) -> RedisStatus:
    try:
        response = await client.ping()
        if response:
            return RedisStatus(connected=True, server_info="Redis server responded with PONG")
        return RedisStatus(connected=False, server_info=f"Unexpected response: {response}")
    except Exception as e:
        return RedisStatus(connected=False, error=str(e))


async def get_connection_status() -> RedisStatus:
    try:
        client = await get_instance()
        return await health_check(client)
    except Exception as e:
        return RedisStatus(connected=False, error=str(e))

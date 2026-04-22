from __future__ import annotations

import json
from typing import Any, AsyncIterator

import redis.asyncio as redis

from paperchat.settings import get_settings


_redis_client: redis.Redis | None = None


def get_redis_client() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        settings = get_settings()
        _redis_client = redis.from_url(settings.redis.endpoint, decode_responses=True)
    return _redis_client


def task_channel(task_id: str) -> str:
    return f"paperchat:tasks:{task_id}:events"


async def publish_task_event(task_id: str, event: dict[str, Any]) -> None:
    client = get_redis_client()
    await client.publish(task_channel(task_id), json.dumps(event, ensure_ascii=False))


async def subscribe_task_events(task_id: str) -> AsyncIterator[dict[str, Any]]:
    client = get_redis_client()
    pubsub = client.pubsub()
    await pubsub.subscribe(task_channel(task_id))
    try:
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=30.0)
            if not message:
                continue
            data = message.get("data")
            if isinstance(data, str):
                yield json.loads(data)
    finally:
        await pubsub.unsubscribe(task_channel(task_id))
        await pubsub.close()

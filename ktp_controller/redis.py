# Standard library imports
import contextlib
import json
import secrets
import typing

# Third-party imports
import redis.asyncio as redis

# Internal imports
import ktp_controller.messages
from ktp_controller import SETTINGS

# Relative imports


__all__ = [
    # Types:
    "RateLimiter",
    "SessionStore",
    "CappedList",
    # Utils:
    "pubsub_send",
    "pubsub",
]


# Utils:


async def pubsub_send(message: ktp_controller.messages.Message, channel: str) -> str:
    message_dict = json.loads(message.model_dump_json())
    async with redis.from_url(SETTINGS.redis_url) as redis_client:
        await redis_client.publish(
            channel,
            json.dumps(
                message_dict,
                ensure_ascii=True,
                separators=(",", ":"),
            ).encode("ascii"),
        )
    return typing.cast(str, message_dict["uuid"])


@contextlib.asynccontextmanager
async def pubsub(channel: str) -> typing.AsyncIterator[typing.Any]:
    async with (
        redis.from_url(SETTINGS.redis_url) as redis_client,
        redis_client.pubsub() as pubsub_,
    ):
        await pubsub_.subscribe(channel)
        try:
            yield pubsub_
        finally:
            await pubsub_.unsubscribe(channel)


class CappedList:
    def __init__(self, key: str, max_size: int, /) -> None:
        if max_size < 0:
            raise ValueError("max_size cannot be less than zero")
        self.__key = f"ktp_controller:CappedList:{key}"
        self.__max_size = max_size

    async def lpush(self, data: typing.Any, /) -> None:
        json_str = json.dumps(data, ensure_ascii=True)
        async with redis.from_url(SETTINGS.redis_url) as redis_client:
            async with redis_client.pipeline() as pipeline:
                pipeline.lpush(self.__key, json_str)
                pipeline.ltrim(self.__key, 0, self.__max_size - 1)
                await pipeline.execute()

    async def getall(self, /) -> list[typing.Any]:
        async with redis.from_url(SETTINGS.redis_url) as redis_client:
            json_strs = await redis_client.lrange(self.__key, 0, -1)
            return [json.loads(s) for s in json_strs]


class SessionStore:
    """Opaque-token, server-side session storage backed by Redis.

    The session cookie only ever carries the random token; the actual
    session data lives here, so a tampered/guessed cookie value simply
    fails to resolve to a session.
    """

    def __init__(self, key: str, ttl_sec: int, /) -> None:
        if ttl_sec < 1:
            raise ValueError("ttl_sec must be greater than zero")
        self.__prefix = f"ktp_controller:SessionStore:{key}"
        self.__ttl_sec = ttl_sec

    def __key(self, session_id: str) -> str:
        return f"{self.__prefix}:{session_id}"

    async def create(self, data: dict[str, typing.Any], /) -> str:
        session_id = secrets.token_urlsafe(32)
        async with redis.from_url(SETTINGS.redis_url) as redis_client:
            await redis_client.set(
                self.__key(session_id),
                json.dumps(data, ensure_ascii=True),
                ex=self.__ttl_sec,
            )
        return session_id

    async def get(self, session_id: str, /) -> dict[str, typing.Any] | None:
        async with redis.from_url(SETTINGS.redis_url) as redis_client:
            json_str = await redis_client.get(self.__key(session_id))
        if json_str is None:
            return None
        return typing.cast("dict[str, typing.Any]", json.loads(json_str))

    async def touch(self, session_id: str, /) -> None:
        async with redis.from_url(SETTINGS.redis_url) as redis_client:
            await redis_client.expire(self.__key(session_id), self.__ttl_sec)

    async def delete(self, session_id: str, /) -> None:
        async with redis.from_url(SETTINGS.redis_url) as redis_client:
            await redis_client.delete(self.__key(session_id))


class RateLimiter:
    """Fixed-window rate limiter, e.g. to slow down login brute-forcing."""

    def __init__(self, key: str, max_hits: int, window_sec: int, /) -> None:
        if max_hits < 1:
            raise ValueError("max_hits must be greater than zero")
        if window_sec < 1:
            raise ValueError("window_sec must be greater than zero")
        self.__prefix = f"ktp_controller:RateLimiter:{key}"
        self.__max_hits = max_hits
        self.__window_sec = window_sec

    async def hit(self, subject: str, /) -> bool:
        """Records a hit for `subject`.

        Returns whether `subject` is still within its rate limit.
        """
        key = f"{self.__prefix}:{subject}"
        async with redis.from_url(SETTINGS.redis_url) as redis_client:
            count = await redis_client.incr(key)
            if count == 1:
                await redis_client.expire(key, self.__window_sec)
        return count <= self.__max_hits

    async def reset(self, subject: str, /) -> None:
        key = f"{self.__prefix}:{subject}"
        async with redis.from_url(SETTINGS.redis_url) as redis_client:
            await redis_client.delete(key)


RAW_ABITTI2_STATS_MESSAGES = CappedList("raw_abitti2_stats_message", 2)

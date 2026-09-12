# Standard library imports
import contextlib
import json
import typing

# Third-party imports
import redis.asyncio as redis

# Internal imports
import ktp_controller.messages

# Relative imports


__all__ = [
    # Utils:
    "pubsub_send",
    "pubsub",
]


# Utils:


async def pubsub_send(message: ktp_controller.messages.Message, channel: str) -> str:
    message_dict = json.loads(message.model_dump_json())
    async with redis.from_url("redis://127.0.0.1") as redis_client:
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
        redis.from_url("redis://127.0.0.1") as redis_client,
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
        async with redis.from_url("redis://127.0.0.1") as redis_client:
            async with redis_client.pipeline() as pipeline:
                pipeline.lpush(self.__key, json_str)
                pipeline.ltrim(self.__key, 0, self.__max_size - 1)
                await pipeline.execute()

    async def getall(self, /) -> list[typing.Any]:
        async with redis.from_url("redis://127.0.0.1") as redis_client:
            json_strs = await redis_client.lrange(self.__key, 0, -1)
            return [json.loads(s) for s in json_strs]


RAW_ABITTI2_STATS_MESSAGES = CappedList("raw_abitti2_stats_message", 2)

import contextlib
import json

import redis.asyncio as redis

import ktp_controller.messages


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
    return message_dict["uuid"]


@contextlib.asynccontextmanager
async def pubsub(channel):
    async with redis.from_url("redis://127.0.0.1") as redis_client:
        async with redis_client.pubsub() as pubsub_:
            await pubsub_.subscribe(channel)
            try:
                yield pubsub_
            finally:
                await pubsub_.unsubscribe(channel)

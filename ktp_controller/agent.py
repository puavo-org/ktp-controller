import contextlib
import json
import uuid

import redis.asyncio as redis


_PUBSUB_CHANNEL = f"ktp-controller__agent_messages__{ str(uuid.uuid4()) }"


async def bleep():
    async with redis.from_url("redis://127.0.0.1") as redis_client:
        await redis_client.publish(
            _PUBSUB_CHANNEL,
            json.dumps(
                {
                    "kind": "bleep",
                    "uuid": str(uuid.uuid4()),
                },
                ensure_ascii=True,
                separators=(",", ":"),
            ).encode("ascii"),
        )


@contextlib.asynccontextmanager
async def pubsub():
    async with redis.from_url("redis://127.0.0.1") as redis_client:
        async with redis_client.pubsub() as pubsub_:
            await pubsub_.subscribe(_PUBSUB_CHANNEL)
            try:
                yield pubsub_
            finally:
                await pubsub_.unsubscribe(_PUBSUB_CHANNEL)

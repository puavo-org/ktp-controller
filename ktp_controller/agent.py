import contextlib
import enum
import json
import uuid

import redis.asyncio as redis


_PUBSUB_CHANNEL = f"ktp-controller__agent_messages__{ str(uuid.uuid4()) }"


async def _pubsub_send(data) -> str:
    uuid_str = str(uuid.uuid4())

    data["uuid"] = uuid_str
    async with redis.from_url("redis://127.0.0.1") as redis_client:
        await redis_client.publish(
            _PUBSUB_CHANNEL,
            json.dumps(
                data,
                ensure_ascii=True,
                separators=(",", ":"),
            ).encode("ascii"),
        )
    return uuid_str


class Command(str, enum.Enum):
    ENABLE_AUTO_CONTROL = "enable_auto_control"
    DISABLE_AUTO_CONTROL = "disable_auto_control"

    def __str__(self) -> str:
        return self.value


async def send_command(command: Command) -> str:
    return _pubsub_send({"kind": "command", "command": str(command)})


@contextlib.asynccontextmanager
async def pubsub():
    async with redis.from_url("redis://127.0.0.1") as redis_client:
        async with redis_client.pubsub() as pubsub_:
            await pubsub_.subscribe(_PUBSUB_CHANNEL)
            try:
                yield pubsub_
            finally:
                await pubsub_.unsubscribe(_PUBSUB_CHANNEL)

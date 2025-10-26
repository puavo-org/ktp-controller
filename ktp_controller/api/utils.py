# Standard library imports
import logging

# Third-party imports
import fastapi
import redis.asyncio as redis


__all__ = [
    "deliver_pubsub_messages_to_websock",
]


# Constants:


_LOGGER = logging.getLogger(__name__)


# Utils:


async def deliver_pubsub_messages_to_websock(
    pubsub: redis.client.PubSub, websock: fastapi.WebSocket
):
    _LOGGER.debug("%s %s", pubsub, websock)
    async for message in pubsub.listen():
        if message and message["type"] == "message":
            data = message["data"].decode("ascii")
            await websock.send_text(data)

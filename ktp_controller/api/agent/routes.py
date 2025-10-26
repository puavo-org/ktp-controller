# Standard library imports
import asyncio
import logging

# Third-party imports
import fastapi  # type: ignore

# Internal imports
import ktp_controller.agent
import ktp_controller.redis
import ktp_controller.api.utils

_LOGGER = logging.getLogger(__name__)


__all__ = [
    "router",
]

router = fastapi.APIRouter(tags=["agent"])


async def _play_ping_pong_with_agent(websock: fastapi.WebSocket):
    async for message in websock.iter_json():
        if message["kind"] == "ping":
            await websock.send_json({"kind": "pong", "uuid": message["uuid"]})
            continue
        _LOGGER.warning("Received and ignored unknown message: %s", message)


@router.websocket("/websocket")
async def _websocket(
    websock: fastapi.WebSocket,
):
    await websock.accept()

    async with ktp_controller.redis.pubsub(
        ktp_controller.agent.PUBSUB_CHANNEL
    ) as pubsub:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(
                ktp_controller.api.utils.deliver_pubsub_messages_to_websock(
                    pubsub, websock
                )
            )
            tg.create_task(_play_ping_pong_with_agent(websock))

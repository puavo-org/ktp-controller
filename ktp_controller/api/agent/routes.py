# Standard library imports
import asyncio
import logging

# Third-party imports
import fastapi  # type: ignore
import fastapi.exceptions  # type: ignore
import redis.asyncio as redis

# Internal imports
import ktp_controller.agent

# from ktp_controller.api.database import get_db


_LOGGER = logging.getLogger(__name__)


__all__ = [
    "router",
]

router = fastapi.APIRouter(tags=["agent"])


@router.post(
    "/enable_auto_control",
    response_model=None,
    summary="Enable auto control.",
)
async def _enable_auto_control():
    await ktp_controller.agent.send_command(
        ktp_controller.agent.Command.ENABLE_AUTO_CONTROL
    )


@router.post(
    "/disable_auto_control",
    response_model=None,
    summary="Disable auto control.",
)
async def _disable_auto_control():
    await ktp_controller.agent.send_command(
        ktp_controller.agent.Command.DISABLE_AUTO_CONTROL
    )


async def _deliver_pubsub_messages_to_agent(
    pubsub: redis.client.PubSub, websock: fastapi.WebSocket
):
    _LOGGER.debug("%s %s", pubsub, websock)
    async for message in pubsub.listen():
        if message and message["type"] == "message":
            data = message["data"].decode("ascii")
            await websock.send_text(data)


async def _play_ping_pong_with_agent(websock: fastapi.WebSocket):
    async for message in websock.iter_json():
        if message["kind"] == "ping":
            await websock.send_json({"kind": "pong", "uuid": message["uuid"]})
            continue
        _LOGGER.warning("Received and ignored unknown message: %s", message)


@router.websocket("/websocket")
async def _websocket(
    websock: fastapi.WebSocket,
    # db: sqlalchemy.orm.Session = fastapi.Depends(get_db),
):
    await websock.accept()

    async with ktp_controller.agent.pubsub() as pubsub:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(_deliver_pubsub_messages_to_agent(pubsub, websock))
            tg.create_task(_play_ping_pong_with_agent(websock))

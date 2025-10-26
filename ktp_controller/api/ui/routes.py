# Standard library imports
import asyncio
import logging

# Third-party imports
import fastapi  # type: ignore
import pydantic

# Internal imports
import ktp_controller.agent
import ktp_controller.redis
import ktp_controller.api.utils

_LOGGER = logging.getLogger(__name__)


__all__ = [
    "router",
]

router = fastapi.APIRouter(tags=["ui"])


@router.post(
    "/async_enable_auto_control",
    response_model=pydantic.UUID4,
    status_code=202,
    summary="""\
Asynchronously enable auto control.
Auto control will be enabled soon after the response is sent.
Return asynchronous message UUID as application/json body.
""",
)
async def _async_enable_auto_control():
    return await ktp_controller.agent.send_command(
        ktp_controller.messages.CommandData(
            command=ktp_controller.messages.Command.ENABLE_AUTO_CONTROL
        )
    )


@router.post(
    "/async_disable_auto_control",
    response_model=pydantic.UUID4,
    status_code=202,
    summary="""\
Asynchronously disable auto control.
Auto control will be disabled soon after the response is sent.
Return asynchronous message UUID as application/json body.
""",
)
async def _async_disable_auto_control():
    return await ktp_controller.agent.send_command(
        ktp_controller.messages.CommandData(
            command=ktp_controller.messages.Command.DISABLE_AUTO_CONTROL
        )
    )


@router.websocket("/websocket")
async def _websocket(websock: fastapi.WebSocket):
    await websock.accept()

    async with ktp_controller.redis.pubsub(ktp_controller.ui.PUBSUB_CHANNEL) as pubsub:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(
                ktp_controller.api.utils.deliver_pubsub_messages_to_websock(
                    pubsub, websock
                )
            )

# Standard library imports
import asyncio
import logging

# Third-party imports
import fastapi
import websockets

# Internal imports
import ktp_controller.api.client
import ktp_controller.messages
import ktp_controller.utils

__all__ = [
    "BrowserSocketRegistry",
    "raw_abitti2_stats_message_listener",
]

_LOGGER = logging.getLogger(__name__)


class BrowserSocketRegistry:
    """Tracks browser WebSocket connections and notifies them of new data.

    Deliberately minimal: unlike ktp_controller.api.utils.PubSubBroadcaster,
    there is exactly one kind of event to fan out, so no channel/pubsub
    abstraction is needed here.
    """

    def __init__(self) -> None:
        self.__websocks: set[fastapi.WebSocket] = set()

    async def register(self, websock: fastapi.WebSocket) -> None:
        self.__websocks.add(websock)

    async def unregister(self, websock: fastapi.WebSocket) -> None:
        self.__websocks.discard(websock)

    async def notify_all(self) -> None:
        for websock in self.__websocks.copy():
            try:
                await websock.send_text("abitti2_stats_changed")
            except Exception as e:
                _LOGGER.error(
                    "Failed to notify browser websocket %r, closing it: %s",
                    websock,
                    e,
                )
                try:
                    await websock.close(code=1000)
                except Exception as e:
                    _LOGGER.error(
                        "Could not close browser websocket %r properly "
                        "(perhaps the connection was already broken): %s",
                        websock,
                        e,
                    )


async def raw_abitti2_stats_message_listener(registry: BrowserSocketRegistry) -> None:
    """Maintains a persistent connection to the API's ui_websocket and
    notifies `registry` whenever UI may need a refresh: on
    abitti2_stats_changed broadcasts (emitted by the API right after
    it saves a message into the Redis-backed
    RAW_ABITTI2_STATS_MESSAGES list that WUI uses for data views).

    Reconnects with exponential backoff on disconnect, mirroring
    ktp_controller.tui.messages.message_loop.

    """
    reconnect_delay = 1
    max_reconnect_delay = 16

    while True:
        try:
            async with websockets.connect(
                ktp_controller.api.client.get_ui_websock_url()
            ) as websock:
                reconnect_delay = 1
                async for data in websock:
                    msg_dict = ktp_controller.utils.json_loads_dict(data)
                    if (
                        msg_dict.get("kind")
                        == ktp_controller.messages.MessageKind.ABITTI2_STATS_CHANGED
                    ):
                        await registry.notify_all()
        except Exception as e:
            _LOGGER.warning(
                "Lost connection to API ui_websocket, reconnecting in %ds: %s",
                reconnect_delay,
                e,
            )
            await asyncio.sleep(reconnect_delay)
            reconnect_delay = min(reconnect_delay * 2, max_reconnect_delay)

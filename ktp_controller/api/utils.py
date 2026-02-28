# Standard library imports
import asyncio
import contextlib
import logging

# Third-party imports
import fastapi
import redis.asyncio as redis


__all__ = [
    "PubSubBroadcaster",
]

_LOGGER = logging.getLogger(__name__)


class PubSubBroadcaster:
    def __init__(self, redis_url: str = "redis://127.0.0.1"):
        self.__redis_url = redis_url
        self.__redis_client = None
        self.__pubsub = None
        self.__registrations: dict[str, list[fastapi.WebSocket]] = {}
        self.__listener_task = None
        self.__registrations_lock = asyncio.Lock()
        self.__stop_event = asyncio.Event()
        self.__start_event = asyncio.Event()

    async def __connect_to_redis_locked(self):
        if self.__redis_client is not None:
            return

        _LOGGER.info("Connecting to Redis...")
        redis_client = redis.from_url(
            self.__redis_url,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_keepalive=True,
            health_check_interval=30,
        )
        await redis_client.ping()
        self.__redis_client = redis_client
        _LOGGER.info("Connected to Redis.")

    async def __subscribe_to_pubsub_locked(self):
        if self.__pubsub is not None:
            return

        _LOGGER.info("Subscribing to pubsub...")
        pubsub = self.__redis_client.pubsub()
        await pubsub.ping()
        self.__pubsub = pubsub

        for channel, websocks in self.__registrations.copy().items():
            for websock in websocks:
                await self.__register_websocket_locked(websock, channel)
        _LOGGER.info("Subscribed to pubsub.")

    async def __connect(self):
        async with self.__registrations_lock:
            await self.__connect_to_redis_locked()
            await self.__subscribe_to_pubsub_locked()

    async def __disconnect_from_redis_locked(self):
        if self.__redis_client is None:
            return
        _LOGGER.info("Disconnecting from Redis...")
        try:
            await self.__redis_client.close()
        finally:
            self.__redis_client = None
            _LOGGER.info("Disconnected from Redis.")

    async def __unsubscribe_from_pubsub_locked(self):
        if self.__pubsub is None:
            return
        _LOGGER.info("Unsubscribing from pubsub...")
        try:
            errors = []
            for channel, websocks in self.__registrations.copy().items():
                for websock in websocks:
                    try:
                        await self.__unregister_websocket_locked(websock, channel)
                    except Exception as e:
                        errors.append(e)
                        continue
            if errors:
                raise ExceptionGroup("Failed to unsubscribe from pubsub", errors)
        finally:
            self.__pubsub = None
            _LOGGER.info("Unsubscribed from pubsub.")

    async def __disconnect(self):
        async with self.__registrations_lock:
            try:
                await self.__unsubscribe_from_pubsub_locked()
            finally:
                await self.__disconnect_from_redis_locked()

    async def __reconnect(self):
        _LOGGER.info("Starting reconnection procedure...")
        reconnect_timeout = 1
        while not self.__stop_event.is_set():
            await asyncio.sleep(reconnect_timeout)
            reconnect_timeout *= 2
            if reconnect_timeout > 16:
                reconnect_timeout = 1
            try:
                await self.__disconnect()
                await self.__connect()
            except (redis.ConnectionError, redis.TimeoutError) as e:
                _LOGGER.warning("Failed to reconnect: %s", e)
                continue
            break
        _LOGGER.info("Reconnection procedure finished.")

    async def __register_websocket_locked(
        self, websock: fastapi.WebSocket, channel: str
    ):
        _LOGGER.info(
            "Registering websocket %r to channel %r...", websock.client, channel
        )

        await self.__pubsub.subscribe(channel)
        self.__registrations.setdefault(channel, []).append(websock)

        _LOGGER.info("Registered websocket %r to channel %r.", websock.client, channel)

    async def __unregister_websocket_locked(
        self, websock: fastapi.WebSocket, channel: str
    ):
        try:
            self.__registrations[channel].remove(websock)
        except (KeyError, ValueError):
            return

        if len(self.__registrations[channel]) > 0:
            return

        _LOGGER.info(
            "Unregistering websocket %r from channel %r...", websock.client, channel
        )

        self.__registrations.pop(channel)

        try:
            await self.__pubsub.unsubscribe(channel)
        except (redis.ConnectionError, redis.TimeoutError) as e:
            _LOGGER.warning(
                "Failed to unsubscribe from Redis pubsub channel %r: %s", channel, e
            )

        _LOGGER.info(
            "Unregistered websocket %r from channel %r.", websock.client, channel
        )

    async def __unicast(
        self,
        websock: fastapi.WebSocket,
        data: str,
        channel: str,
        timeout: float = 2.0,
    ):
        try:
            await asyncio.wait_for(websock.send_text(data), timeout=timeout)
        except asyncio.TimeoutError:
            _LOGGER.warning(
                "Sending data to websocket %r, registered to channel %r, timeouted. "
                "Unregistering and closing the connection.",
                websock,
                channel,
            )
            await websock.close(code=1000)

    async def __broadcast(self, message):
        data, channel = message["data"], message["channel"]

        errors = []
        tasks = []
        for websock in self.__registrations.get(channel, []).copy():
            tasks.append(self.__unicast(websock, data, channel))
        errors = await asyncio.gather(*tasks, return_exceptions=True)
        if errors:
            raise ExceptionGroup(
                "Failed to broadcast message %s to some of the subscribed websockets.",
                errors,
            )

    async def __read_message(self):
        message = await self.__pubsub.get_message(
            ignore_subscribe_messages=True, timeout=1.0
        )
        if message is None:
            return None
        if message["type"] != "message":
            _LOGGER.warning(
                "Received message of type %r. Not doing anything with it.",
                message["type"],
            )
            return None

        return message

    async def __listen(self):
        """Read messages from Redis and broadcast them to WebSockets.

        If connection to Redis fails, reconnect to Redis with exponential reconnect timeout.
        """
        is_initial_connect = True
        try:
            while not self.__stop_event.is_set():
                try:
                    if is_initial_connect:
                        is_initial_connect = False
                        await self.__connect()
                    self.__start_event.set()
                    message = await self.__read_message()
                except (redis.ConnectionError, redis.TimeoutError) as e:
                    _LOGGER.error("PubSubBroadcaster encountered error: %s", e)
                    await self.__reconnect()
                else:
                    if message is None:
                        continue
                    await self.__broadcast(message)
        finally:
            with contextlib.suppress(asyncio.CancelledError):
                await self.__disconnect()

    async def register_websocket(self, websock: fastapi.WebSocket, channel: str):
        async with self.__registrations_lock:
            await self.__register_websocket_locked(websock, channel)

    async def unregister_websocket(self, websock: fastapi.WebSocket, channel: str):
        async with self.__registrations_lock:
            await self.__unregister_websocket_locked(websock, channel)

    async def start(self):
        _LOGGER.info("Starting PubSubBroadcaster...")
        if self.__listener_task is not None:
            raise RuntimeError("PubSubBroadcaster is already started")

        self.__listener_task = asyncio.create_task(self.__listen())

        await self.__start_event.wait()

        _LOGGER.info("Started PubSubBroadcaster.")

    async def stop(self):
        _LOGGER.info("Stopping PubSubBroadcaster...")
        self.__stop_event.set()
        if self.__listener_task:
            self.__listener_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.__listener_task
        _LOGGER.info("Stopped PubSubBroadcaster.")

"""
Asyncio utils
"""

# Standard library imports
import asyncio
import logging
import os.path
import signal
import typing

# Third-party imports
from asyncinotify import Inotify, Mask

__all__ = [
    "FileMonitor",
    "new_event_loop",
]


class FileMonitor:
    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        path: str,
        cb: typing.Callable[[typing.Any], typing.Awaitable[typing.Any]],
    ) -> None:
        if not os.path.exists(path):
            raise FileNotFoundError(path)
        self.__loop = loop

        # Initialize asyncinotify Inotify instance
        self.__watcher = Inotify()

        # Add a watch using Mask enums
        self.__watcher.add_watch(
            path,
            Mask.MODIFY | Mask.CREATE | Mask.DELETE,
        )

        self.__task: asyncio.Task[None] | None = None
        self.__cb = cb

    async def __run(self) -> None:
        # asyncinotify provides an async generator,
        # so no explicit .setup(loop) is required anymore
        async for event in self.__watcher:
            await self.__cb(event)

    def start(self) -> None:
        self.__task = self.__loop.create_task(self.__run())

    def stop(self) -> None:
        self.__watcher.close()
        if self.__task is not None:
            self.__task.cancel()


def new_event_loop(
    stop_signals: tuple[signal.Signals, ...] = (
        signal.SIGTERM,
        signal.SIGINT,
        signal.SIGQUIT,
        signal.SIGTSTP,
    ),
    logger: logging.Logger | None = None,
) -> asyncio.AbstractEventLoop:
    if logger is None:
        logger = logging.getLogger()

    loop = asyncio.new_event_loop()

    # Keep strong references to background tasks so they are not garbage
    # collected before they finish (see asyncio.ensure_future docs).
    background_tasks: set[asyncio.Future[typing.Any]] = set()

    async def _stop_loop() -> None:
        loop.stop()

    def _stop(sig: signal.Signals) -> None:
        for stop_signal in stop_signals:
            signal.signal(stop_signal, signal.SIG_IGN)
        logger.info("stopping due to caught signal %r", sig)
        for task in asyncio.all_tasks():
            task.cancel()
        stop_task = asyncio.ensure_future(_stop_loop())
        background_tasks.add(stop_task)
        stop_task.add_done_callback(background_tasks.discard)

    for sig in stop_signals:
        loop.add_signal_handler(sig, _stop, sig)

    return loop

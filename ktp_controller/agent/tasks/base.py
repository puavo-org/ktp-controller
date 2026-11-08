# Standard library imports
import asyncio
import contextlib
import logging
import typing

_LOGGER = logging.getLogger(__name__)


__all__ = [
    "SHUTDOWN_EVENT",
    "UnexpectedCancel",
    "task_guard",
    "periodic",
    "CoalescingQueue",
    "resolve_all",
    "reject_all",
]


SHUTDOWN_EVENT = asyncio.Event()


class UnexpectedCancel(Exception):
    pass


@contextlib.asynccontextmanager
async def task_guard(
    name: str, *, on_exit_coro: typing.Awaitable[typing.Any] | None = None
) -> typing.AsyncIterator[None]:
    try:
        _LOGGER.info("Starting task %r...", name)
        yield
    except asyncio.CancelledError as err:
        if SHUTDOWN_EVENT.is_set():
            # That's normal, the task was cancelled while the agent is shutting down.
            raise
        raise UnexpectedCancel(f"Unexpected cancellation of task {name!r}!") from err
    finally:
        if SHUTDOWN_EVENT.is_set():
            _LOGGER.info("Task %r was shut down.", name)
        else:
            _LOGGER.warning("Task %r was aborted!", name)
        if on_exit_coro is not None:
            await on_exit_coro


async def periodic(
    name: str,
    interval_sec: float,
    body: typing.Callable[[], typing.Awaitable[None]],
    *,
    on_error_message: str,
) -> None:
    """Run body() immediately, then every interval_sec, until shutdown.

    Exceptions raised by body() are logged and swallowed, so one failed
    iteration does not stop subsequent ones.
    """
    started = False
    async with task_guard(name):
        while not SHUTDOWN_EVENT.is_set():
            try:
                if started:
                    await asyncio.sleep(interval_sec)
                started = True
                await body()
            except Exception:
                _LOGGER.exception(on_error_message)


_P = typing.TypeVar("_P")
_R = typing.TypeVar("_R")


class CoalescingQueue(typing.Generic[_P, _R]):
    """Single-slot producer/consumer queue.

    At most one batch of payloads is ever pending (submitted but not
    yet picked up by consume()) at a time: concurrent request() calls
    made while a batch is pending just append their payload (and a
    waiter future) to that same batch instead of creating a new one.
    So a burst of N request() calls while a batch is in flight results
    in at most one more run of the consumer's task body, and every
    caller in that burst gets the result of whichever run ends up
    servicing its batch.
    """

    def __init__(self) -> None:
        self.__channel: asyncio.Queue[list[tuple[_P, asyncio.Future[_R]]]] = (
            asyncio.Queue(maxsize=1)
        )
        self.__pending: list[tuple[_P, asyncio.Future[_R]]] | None = None

    async def request(self, payload: _P) -> _R:
        future: asyncio.Future[_R] = asyncio.get_running_loop().create_future()
        if self.__pending is None:
            self.__pending = []
            self.__channel.put_nowait(self.__pending)
        self.__pending.append((payload, future))
        return await future

    async def consume(self) -> list[tuple[_P, asyncio.Future[_R]]]:
        batch = await self.__channel.get()
        if self.__pending is batch:
            self.__pending = None
        return batch


def resolve_all(futures: typing.Iterable[asyncio.Future[_R]], result: _R) -> None:
    for future in futures:
        if not future.done():
            future.set_result(result)


def reject_all(
    futures: typing.Iterable[asyncio.Future[_R]], exc: BaseException
) -> None:
    for future in futures:
        if not future.done():
            future.set_exception(exc)

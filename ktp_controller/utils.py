# Standard library imports
import abc
import base64
import logging
import os
import signal
import sys
import typing
import urllib.parse

# Third-party imports
import websocket  # type: ignore


_LOGGER = logging.getLogger(__file__)


def get_url(
    host: str,
    path: str,
    *,
    use_websocket: bool = False,
    use_tls: bool = True,
) -> str:
    """Construct valid URL

    >>> get_url('example.invalid', '/what/not')
    'https://example.invalid/what/not'

    >>> get_url('example.invalid', 'another/path/without/leading/slash', use_websocket=True)
    'wss://example.invalid/another/path/without/leading/slash'
    """

    path = path.removeprefix("/")

    if use_websocket:
        scheme = "ws"
    else:
        scheme = "http"

    if use_tls:
        scheme = f"{scheme}s"

    return f"{scheme}://{host}/{path}"


def sigawaresleep(seconds):
    siginfo = signal.sigtimedwait(signal.Signals, seconds)
    if siginfo:
        signal.raise_signal(siginfo.si_signo)


def common_term_signal(func):
    for quit_signal in [
        signal.SIGINT,
        signal.SIGTERM,
        signal.SIGHUP,
        signal.SIGUSR1,
        signal.SIGUSR2,
        signal.SIGALRM,
        signal.SIGQUIT,
    ]:
        signal.signal(quit_signal, lambda s, e: func())


def get_basic_auth(username: str, password: str) -> str:
    auth = base64.b64encode(f"{username}:{password}".encode("ascii")).decode("ascii")
    return f"Basic {auth}"


def open_websock(
    host: str,
    path: str,
    *,
    params: typing.Optional[typing.Dict[str, str]] = None,
    header: typing.Optional[typing.Dict[str, str]] = None,
    timeout: int = 5,
    use_tls: bool = True,
) -> websocket.WebSocket:
    if header is None:
        header = {}

    url = get_url(host, path, use_websocket=True, use_tls=use_tls)

    if params is not None:
        url = f"{url}?{urllib.parse.urlencode(params)}"

    websock = websocket.WebSocket()
    _LOGGER.debug("connecting websocket to %r", url)
    websock.connect(
        url,
        connection="Connection: Upgrade",
        header=header,
        timeout=timeout,
    )

    return websock


def readfirstline(filepath, encoding=sys.getdefaultencoding()):
    with open(filepath, "r", encoding=encoding) as f:
        return f.readline().rstrip(os.linesep)


class Listener(abc.ABC):
    def __init__(self, failure_sleep=5):
        self.__websock = None
        self.__is_running = False
        self.__failure_sleep = failure_sleep

    def __quit(self):
        self.__is_running = False

    def __run(self):
        self.__is_running = True
        while self.__is_running:
            try:
                _LOGGER.info("opening websocket connection")
                self.__websock = self._open_websock()

                while self.__is_running:
                    try:
                        message = self.__websock.recv()
                    except websocket.WebSocketTimeoutException:
                        _LOGGER.info("websocket recv timeout")
                        self._on_recv_timeout()
                        continue

                    _LOGGER.debug("received %r", message)

                    try:
                        validated_message = self._validate_message(message)
                    except ValueError as value_error:
                        _LOGGER.warning(
                            "received invalid message, ignoring it: %s",
                            value_error,
                        )
                    else:
                        if not self._handle_validated_message(validated_message):
                            _LOGGER.error(
                                "validated message left unhandled: %s",
                                validated_message,
                            )

                break
            except websocket.WebSocketException as websocket_exception:
                _LOGGER.error("websocket failed: %s", websocket_exception)
            except ConnectionError as connection_error:
                _LOGGER.error("connection failed: %s", connection_error)
            except:
                _LOGGER.exception("something failed")
            finally:
                if self.__websock:
                    _LOGGER.info("closing websocket connection")
                    self.__websock.close()
                    self.__websock = None

            sigawaresleep(self.__failure_sleep)

        _LOGGER.info("bye")

    @abc.abstractmethod
    def _handle_validated_message(self, validated_message) -> bool:
        ...

    @abc.abstractmethod
    def _open_websock(self):
        ...

    def _on_recv_timeout(self):
        pass

    def _send(self, message, encoder):
        message = encoder(message)
        _LOGGER.debug("sending %r", message)
        self.__websock.send(message)

    def _validate_message(self, message):
        return message

    def quit(self):
        return self.__quit()

    def run(self):
        return self.__run()

# Standard library imports
import base64
import logging
import os
import signal
import sys
import typing
import urllib.parse

# Third-party imports
import websocket


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
    timeout: int = 45,
) -> websocket.WebSocket:
    if header is None:
        header = {}

    url = get_url(host, path, use_websocket=True)

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

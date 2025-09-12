import signal


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

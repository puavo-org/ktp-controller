# Standard library imports
import base64
import contextlib
import datetime
import errno
import fcntl
import hashlib
import io
import json
import locale
import logging
import logging.handlers
import os
import os.path
import sys
import typing
import urllib.parse
import warnings

__all__ = [
    # Utils:
    "sha256",
    "open_atomic_write",
    "copy_atomic",
    "json_loads_dict",
    "get_url",
    "get_basic_auth",
    "readfirstline",
    "websock_send_json",
]


_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel(logging.DEBUG)


class LineBufferedLoggingStream(io.TextIOWrapper):
    def __init__(self, logger: logging.Logger, level: int) -> None:
        self.__buffer = io.BytesIO()
        self.__logger = logger
        self.__level = level
        super().__init__(self.__buffer, line_buffering=True)

    def flush(self) -> None:
        with self.__buffer.getbuffer() as buf:
            s = buf.tobytes().decode(locale.getencoding())
            if s:
                self.__logger.log(self.__level, s)
        self.__buffer.truncate(0)


def sha256(filepath: str, chunk_size_bytes: int = 1024**2) -> str:
    if chunk_size_bytes < 1:
        raise ValueError(
            "invalid chunk_size, must be greater than zero", chunk_size_bytes
        )

    cs = hashlib.sha256()
    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(chunk_size_bytes)
            if not chunk:
                break
            cs.update(chunk)

    return cs.hexdigest()


@contextlib.contextmanager
def open_atomic_write(
    dest_filepath: str,
    exclusive: bool = False,
    encoding: str | None = None,
    do_makedirs: bool = False,
) -> typing.Iterator[typing.IO[typing.Any]]:
    if exclusive and os.path.exists(dest_filepath):
        raise FileExistsError(dest_filepath)

    tmpfilemode = "w"

    if encoding is None:
        tmpfilemode = f"{tmpfilemode}b"

    if do_makedirs:
        dest_dirpath = os.path.dirname(dest_filepath)
        try:
            os.makedirs(dest_dirpath)
        except FileExistsError:
            pass

    tmp_dest_filepath = f"{dest_filepath}.ktp_controller_open_atomic_write_tmp"
    try:
        with open(tmp_dest_filepath, tmpfilemode, encoding=encoding) as tmp_dest_file:
            yield tmp_dest_file
        os.rename(tmp_dest_filepath, dest_filepath)
    finally:
        try:
            os.unlink(tmp_dest_filepath)
        except FileNotFoundError:
            pass


def copy_atomic(src_filepath: str, dest_filepath: str, exclusive: bool = False) -> None:
    with (
        open(src_filepath, "rb") as src_file,
        open_atomic_write(
            dest_filepath, exclusive=exclusive, encoding=None
        ) as dest_file,
    ):
        while True:
            data = src_file.read(4096)
            if not data:
                break
            dest_file.write(data)


def json_loads_dict(string: str | bytes) -> dict[str, typing.Any]:
    try:
        data = json.loads(string)
    except Exception as e:
        raise ValueError("string is not valid JSON") from e

    if not isinstance(data, dict):
        raise ValueError("data is not a dict")

    return data


def get_url(
    host: str,
    path: str,
    *,
    params: typing.Mapping[str, typing.Any] | None = None,
    scheme: str = "https",
) -> str:
    r"""Construct valid URL

    >>> get_url('example.invalid', '/what/not')
    'https://example.invalid/what/not'

    >>> get_url('example.invalid', 'another/path/without/leading/slash', scheme='wss')
    'wss://example.invalid/another/path/without/leading/slash'

    >>> get_url('example.invalid:8899', '/what/not', scheme='ftp')
    'ftp://example.invalid:8899/what/not'

    >>> get_url('http://example.invalid:8899', '/what/not')
    Traceback (most recent call last):
    ...
    ValueError: ('invalid host', 'http://example.invalid:8899')

    >>> get_url('example.invalid:8899/', '/what/not/', params={"myid": 7, "color": "black&white right\n"})
    'https://example.invalid:8899/what/not/?myid=7&color=black%26white+right%0A'
    """

    path = path.removeprefix("/")
    host = host.removesuffix("/")

    if host.partition("://")[1]:
        raise ValueError("invalid host", host)

    url = f"{scheme}://{host}/{path}"

    if params is not None:
        url = f"{url}?{urllib.parse.urlencode(params)}"

    return url


def get_basic_auth(username: str, password: str) -> dict[str, str]:
    auth = base64.b64encode(f"{username}:{password}".encode()).decode("ascii")
    return {"Authorization": f"Basic {auth}"}


def readfirstline(filepath: str, encoding: str | None = None) -> str:
    if encoding is None:
        encoding = sys.getdefaultencoding()
    with open(filepath, encoding=encoding) as f:
        return f.readline().rstrip(os.linesep)


async def websock_send_json(websock: typing.Any, data: typing.Any) -> str:
    message = json.dumps(
        data,
        ensure_ascii=True,
        separators=(",", ":"),
    )
    await websock.send(message)

    return message


def utcnow() -> datetime.datetime:
    return datetime.datetime.utcnow().replace(tzinfo=datetime.UTC)


def now() -> datetime.datetime:
    return datetime.datetime.now().astimezone()


def strfdt(dt: datetime.datetime) -> str:
    return dt.strftime(f"%Y-%m-%dT%H:%M:%S.{dt.microsecond // 1000:0>3}%z")


def utcnow_str() -> str:
    return strfdt(utcnow())


def now_str() -> str:
    return strfdt(now())


def is_valid_filename(filename: str) -> bool:
    """
    >>> is_valid_filename('foo.json')
    True
    >>> is_valid_filename('/bar/foo.json')
    False
    >>> is_valid_filename('.')
    False
    >>> is_valid_filename('..')
    False
    >>> is_valid_filename('...')
    True
    >>> is_valid_filename('.' * 255)
    True
    >>> is_valid_filename('.' * 256)
    False
    >>> is_valid_filename('foo\\0')
    False
    >>> is_valid_filename('foo\\1')
    True
    >>> is_valid_filename('foo\\nbar')
    True
    >>> is_valid_filename('♆o_$?.! !')
    True
    >>> is_valid_filename('')
    False
    """

    return (
        isinstance(filename, str)
        and len(filename) > 0
        and "\0" not in filename
        and "/" not in filename
        and len(filename.encode("utf-8")) <= 255
        and filename not in (".", "..")
    )


def check_filename(filename: str) -> None:
    if not is_valid_filename(filename):
        raise ValueError("invalid filename", filename)


def bytes_stream(filepath: str, chunk_size: int = 4096) -> typing.Iterator[bytes]:
    with open(filepath, "rb") as f:
        while True:
            data = f.read(chunk_size)
            if not data:
                break
            yield data


@contextlib.contextmanager
def singleton() -> typing.Iterator[None]:
    this_prog_path = os.path.realpath(sys.argv[0])
    with open(this_prog_path, "rb") as lock_file:
        try:
            fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as io_error:
            if io_error.errno != errno.EAGAIN:
                raise
            raise RuntimeError(
                f"program {this_prog_path!r} is already running)"
            ) from io_error
        yield


def relatimestr(
    dt: str | datetime.datetime, *, now: datetime.datetime | None = None
) -> str:
    """
    >>> relatimestr(datetime.datetime(1970, 1, 1, 10, 0, 0), now=datetime.datetime(1970, 1, 1, 11, 5, 3))
    '1h 5m 3s ago'

    >>> relatimestr("1970-01-01T10:00:00", now=datetime.datetime(1970, 1, 1, 10, 0, 0))
    'now'

    >>> relatimestr(datetime.datetime(1970, 1, 1, 10, 0, 0), now=datetime.datetime(1970, 2, 3, 11, 5, 3))
    '33d 1h 5m 3s ago'

    >>> relatimestr(datetime.datetime(1970, 1, 1, 10, 0, 0, tzinfo=datetime.UTC), now=datetime.datetime(1970, 2, 3, 11, 5, 3, tzinfo=datetime.UTC))
    '33d 1h 5m 3s ago'

    >>> relatimestr("1970-01-01T10:00:00Z", now=datetime.datetime(1970, 2, 3, 11, 5, 3, tzinfo=datetime.timezone(datetime.timedelta(seconds=7200), 'EET')))
    '32d 23h 5m 3s ago'

    >>> relatimestr(datetime.datetime(1970, 1, 1, 10, 0, 0), now=datetime.datetime(1970, 2, 3, 11, 5, 3, tzinfo=datetime.UTC))
    Traceback (most recent call last):
    ...
    ValueError: dt and now must both be naive or have have time zone information

    >>> relatimestr(datetime.datetime(1970, 1, 1, 10, 0, 0, tzinfo=datetime.UTC), now="1970-02-03T11:05:03")
    Traceback (most recent call last):
    ...
    ValueError: dt and now must both be naive or have have time zone information

    >>> relatimestr(datetime.datetime(1970, 1, 1, 10, 0, 0), now=datetime.datetime(1970, 1, 1, 9, 0, 0))
    'in 1h 0m 0s'
    """
    if now is None:
        now = utcnow()
    elif isinstance(now, str):
        now = datetime.datetime.fromisoformat(now)

    if isinstance(dt, str):
        dt = datetime.datetime.fromisoformat(dt)

    dt_is_naive = False
    if dt.tzinfo is None:
        dt_is_naive = True

    now_is_naive = False
    if now.tzinfo is None:
        now_is_naive = True

    if dt_is_naive != now_is_naive:
        raise ValueError(
            "dt and now must both be naive or have have time zone information"
        )

    now_local: datetime.datetime = now.astimezone()
    dt_local: datetime.datetime = dt.astimezone()

    if dt_local == now_local:
        return "now"

    secs_ago: int = round((now_local - dt_local).total_seconds())
    preposition = ""
    postposition = " ago"
    if secs_ago < 0:
        preposition = "in "
        postposition = ""

    secs = abs(secs_ago)

    if secs < 60:
        return f"{preposition}{secs}s{postposition}"

    mins, secs = divmod(secs, 60)
    if mins < 60:
        return f"{preposition}{mins}m {secs}s{postposition}"

    hours, mins = divmod(mins, 60)
    if hours < 24:
        return f"{preposition}{hours}h {mins}m {secs}s{postposition}"

    days, hours = divmod(hours, 24)
    return f"{preposition}{days}d {hours}h {mins}m {secs}s{postposition}"


def ago(dt: str | datetime.datetime, *, now: datetime.datetime | None = None) -> str:
    warnings.warn(
        "ktp_controller.utils.ago() is deprecated, please use ktp_controller.utils.relatimestr() instead. ktp_controller.utils.ago() will be removed in near future.",
        category=FutureWarning,
        stacklevel=2,
    )
    return relatimestr(dt, now=now)


def is_puavo_os() -> bool:
    return os.path.exists("/etc/puavo")


def logging_singleton_app(
    main_func: typing.Callable[[], int],
    logger: logging.Logger,
    stderr_logging_level: int | None = logging.ERROR,
    stdout_logging_level: int | None = logging.WARNING,
) -> typing.NoReturn:
    original_stderr = sys.stderr

    if stderr_logging_level is not None:
        sys.stderr = LineBufferedLoggingStream(logger, stderr_logging_level)
    if stdout_logging_level is not None:
        sys.stdout = LineBufferedLoggingStream(logger, stdout_logging_level)

    logging_handlers = [
        logging.handlers.SysLogHandler(address="/dev/log"),
        logging.StreamHandler(original_stderr),
    ]

    logging.basicConfig(
        level=logging.INFO,
        handlers=logging_handlers,
        force=True,
    )
    try:
        logger.info("acquiring singleton program lock")
        with singleton():
            logger.info("calling main function")
            status = main_func()
        logger.log(
            logging.INFO if status == 0 else logging.ERROR,
            "returned from main function, status %d",
            status,
        )
    except Exception:
        logger.exception("failed")
        raise
    sys.exit(status)


def traverse_dict(
    d: dict[str, typing.Any],
) -> typing.Iterator[tuple[dict[str, typing.Any], str, typing.Any]]:
    for key, value in d.items():
        if isinstance(value, dict):
            yield from traverse_dict(value)
        else:
            yield (d, key, value)


def agofy_dict(
    report: dict[str, typing.Any],
    ago_func: typing.Callable[[str], str] = ago,
) -> None:
    for d, key, value in traverse_dict(report):
        if key.endswith("_at"):
            try:
                d[key] += f" ({ago_func(value)})"
            except ValueError:
                continue
